"""Ferramentas de diagnóstico para serviços systemd.

Este módulo agrega uma rotina completa de recolha de informação de
diagnóstico para serviços geridos pelo systemd. A rotina foi organizada
com base numa checklist operacional que cobre identificação do contexto,
estado do systemd, logs, verificações de binários/dependências, rede e
outros aspetos relevantes para suporte.

Pode ser utilizado como script autónomo:

```
python -m app.utils.service_diagnostics <servico>.service
```

Existem várias opções para ajustar a recolha (por exemplo caminhos de log
adicionais, portas esperadas, pacote apt a verificar, etc.). Executar com
`--help` para ver a lista completa de parâmetros suportados.
"""

from __future__ import annotations

import argparse
import dataclasses
import getpass
import grp
import os
import platform
import pwd
import shlex
import shutil
import socket
import stat
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


ERROR_PATTERNS = [
    "ERROR",
    "Traceback",
    "Permission denied",
    "OSError",
    "ImportError",
    "FileNotFoundError",
    "DENIED",
    "audit",
]


@dataclasses.dataclass
class CommandResult:
    command: Sequence[str] | str
    returncode: int
    stdout: str
    stderr: str
    error: str | None = None

    def format(self) -> str:
        cmd_display = (
            self.command
            if isinstance(self.command, str)
            else " ".join(shlex.quote(part) for part in self.command)
        )
        header = f"$ {cmd_display}\n(exit={self.returncode})"
        if self.error:
            return f"{header}\n[erro ao executar comando: {self.error}]"
        body_parts: list[str] = [header]
        if self.stdout.strip():
            body_parts.append("stdout:\n" + self.stdout.rstrip())
        if self.stderr.strip():
            body_parts.append("stderr:\n" + self.stderr.rstrip())
        return "\n".join(body_parts)


def run_command(command: Sequence[str] | str, *, timeout: int = 60) -> CommandResult:
    """Executa um comando no shell e devolve um ``CommandResult``.

    O comando é executado em modo texto e sem ``check`` para que erros sejam
    reportados e não causem exceções que interrompam a recolha.
    """

    if isinstance(command, str):
        shell = True
        cmd_display: Sequence[str] | str = command
    else:
        shell = False
        cmd_display = command

    try:
        completed = subprocess.run(
            command if shell else list(command),
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:  # comando inexistente
        return CommandResult(cmd_display, 127, "", "", error=str(exc))
    except subprocess.TimeoutExpired as exc:  # comando bloqueou
        stdout = exc.stdout.decode() if exc.stdout else ""
        stderr = exc.stderr.decode() if exc.stderr else ""
        return CommandResult(cmd_display, 124, stdout, stderr, error="timeout")

    return CommandResult(cmd_display, completed.returncode, completed.stdout, completed.stderr)

def _format_path(path: Path) -> str:
    try:
        stat_info = path.stat()
    except FileNotFoundError:
        return f"{path} — inexistente"

    mode = stat.filemode(stat_info.st_mode)
    owner = pwd.getpwuid(stat_info.st_uid).pw_name
    group = grp.getgrgid(stat_info.st_gid).gr_name
    size = stat_info.st_size
    mtime = datetime.fromtimestamp(stat_info.st_mtime).isoformat(sep=" ")
    return f"{path} — {mode} {owner}:{group} {size} bytes (mtime: {mtime})"


def _tail_file(path: Path, *, lines: int = 50) -> str:
    if not path.exists():
        return f"[ficheiro inexistente: {path}]"
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            content = fh.readlines()
    except OSError as exc:
        return f"[erro ao ler {path}: {exc}]"
    tail = content[-lines:]
    return "".join(tail).rstrip()


def _detect_exec_from_systemd(service: str) -> tuple[Path | None, dict[str, str]]:
    props = {
        "FragmentPath": "",
        "FragmentTimestamp": "",
        "ExecStart": "",
        "User": "",
        "MainPID": "",
        "EnvironmentFile": "",
    }

    for key in props:
        result = run_command(["systemctl", "show", service, f"--property={key}", "--value"])
        if result.returncode == 0:
            props[key] = result.stdout.strip()
        else:
            props[key] = ""

    exec_path: Path | None = None
    if props["ExecStart"]:
        raw = props["ExecStart"].splitlines()[0]
        if raw:
            try:
                parts = shlex.split(raw)
            except ValueError:
                parts = raw.split(maxsplit=1)
            if parts:
                exec_path = Path(parts[0])
    return exec_path, props


def _resolve_exec_path(service: str, override: str | None) -> tuple[Path | None, dict[str, str]]:
    if override:
        return Path(override).resolve(), {}
    exec_path, props = _detect_exec_from_systemd(service)
    if exec_path is None:
        return None, props
    return exec_path.resolve(), props


def _check_user_exists(username: str) -> tuple[bool, str]:
    if not username:
        return False, "(User não definido na unit — assume-se root)"
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False, f"Utilizador {username!r} inexistente"
    return True, f"Utilizador {username!r} encontrado"


def _can_user_write(path: Path, username: str) -> str:
    if not username:
        username = "root"
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        return f"[utilizador {username!r} desconhecido]"

    try:
        st = path.stat()
    except FileNotFoundError:
        return f"[diretório inexistente: {path}]"

    mode = st.st_mode
    owner_ok = st.st_uid == pw.pw_uid and bool(mode & stat.S_IWUSR)
    group_ok = False
    try:
        group = grp.getgrgid(st.st_gid)
    except KeyError:
        group = None
    if group and pw.pw_gid == group.gr_gid:
        group_ok = bool(mode & stat.S_IWGRP)
    others_ok = bool(mode & stat.S_IWOTH)
    effective = owner_ok or group_ok or others_ok
    details = "+".join(
        part
        for part, ok in (
            ("owner", owner_ok),
            ("group", group_ok),
            ("others", others_ok),
        )
        if ok
    )
    if not details:
        details = "sem permissões de escrita" if not effective else ""
    return f"{path} — {'pode escrever' if effective else 'sem acesso'} ({details or '---'})"


def _check_expected_ports(ports: Iterable[int]) -> tuple[list[str], list[str]]:
    listeners: list[str] = []
    conflicts: list[str] = []
    if not ports:
        return listeners, conflicts

    result = run_command(["ss", "-ltnp"])
    if result.returncode != 0:
        conflicts.append("Falha ao executar ss -ltnp")
        return listeners, conflicts

    lines = result.stdout.splitlines()
    for port in ports:
        pattern = f":{port}"
        matches = [line for line in lines if pattern in line]
        if matches:
            listeners.extend(matches)
        else:
            conflicts.append(f"Porta {port} não está a ser escutada")
    return listeners, conflicts


def _test_tcp_connection(host: str, port: int, timeout: float = 2.0) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except Exception as exc:  # noqa: BLE001 - queremos a mensagem literal
        return f"Falha: {exc}"
    finally:
        try:
            sock.close()
        except OSError:
            pass
    return "Sucesso"


def _collect_firewall_info() -> list[str]:
    outputs: list[str] = []
    for cmd in (["ufw", "status"], ["iptables", "-L"]):
        result = run_command(cmd)
        outputs.append(result.format())
    return outputs


def _check_virtualenv(exec_path: Path) -> str:
    for parent in exec_path.parents:
        venv = parent / ".venv"
        if venv.is_dir():
            pip = venv / "bin" / "python"
            if pip.exists():
                result = run_command([str(pip), "-m", "pip", "check"])
                return (
                    f"Ambiente virtual detectado em {venv}\n" + result.format()
                )
    return "Nenhum ambiente virtual (.venv) detectado junto ao executável."


def _get_summary_state(active_result: CommandResult | None) -> str:
    if not active_result or active_result.returncode != 0:
        if active_result and active_result.stdout.strip():
            return active_result.stdout.strip()
        return "desconhecido"
    return active_result.stdout.strip() or "desconhecido"


def build_report(args: argparse.Namespace) -> str:
    start_ts = datetime.now()
    start_monotonic = time.monotonic()

    sections: list[str] = []
    probable_causes: list[str] = []
    recommendations: list[str] = []

    exec_path, systemd_props = _resolve_exec_path(args.service, args.exec_path)

    # 1. Identificação e contexto
    identification_lines: list[str] = []
    identification_lines.append(f"Serviço alvo: {args.service}")
    if exec_path:
        identification_lines.append(f"Executável (resolvido): {exec_path}")
    elif args.exec_path:
        identification_lines.append(f"Executável (forçado): {args.exec_path}")
    else:
        identification_lines.append("Executável: não foi possível determinar via systemd")
    identification_lines.append(f"Data/hora do diagnóstico: {start_ts.isoformat(sep=' ')}")
    identification_lines.append(f"Utilizador em execução: {getpass.getuser()}")
    identification_lines.append(f"Sistema: {platform.platform()} ({platform.version()})")
    identification_lines.append(run_command(["lsb_release", "-a"]).format())
    identification_lines.append(run_command(["uname", "-r"]).format())
    identification_lines.append(run_command(["uptime", "-p"]).format())
    identification_lines.append(run_command(["last", "reboot", "-n", "1"]).format())
    sections.append("\n".join(["## 1. Identificação e contexto", *identification_lines]))

    # 2. Estado do systemd (serviço)
    status_result = run_command(["systemctl", "status", args.service, "--no-pager"])
    is_enabled_result = run_command(["systemctl", "is-enabled", args.service])
    is_active_result = run_command(["systemctl", "is-active", args.service])
    state_lines = [status_result.format(), is_enabled_result.format(), is_active_result.format()]
    main_pid = systemd_props.get("MainPID", "")
    if main_pid:
        state_lines.append(f"PID principal reportado: {main_pid}")
    unit_user = systemd_props.get("User", "") or "root (por omissão)"
    state_lines.append(f"User= {unit_user}")
    sections.append("\n".join(["## 2. Estado do systemd (serviço)", *state_lines]))

    # 3. Logs do serviço
    journal_lines = run_command(
        ["journalctl", "-u", args.service, "-n", str(args.journal_lines), "--no-pager"]
    )
    log_section_lines = [journal_lines.format()]
    filtered_errors: list[str] = []
    if journal_lines.stdout:
        for line in journal_lines.stdout.splitlines():
            if any(pattern.lower() in line.lower() for pattern in ERROR_PATTERNS):
                filtered_errors.append(line)
    if filtered_errors:
        log_section_lines.append("Linhas com erros conhecidos:")
        log_section_lines.extend(filtered_errors)
        probable_causes.append("Erros encontrados no journalctl")

    for log_path in args.log_path:
        path = Path(log_path)
        log_section_lines.append(_format_path(path))
        log_section_lines.append("Últimas linhas:")
        log_section_lines.append(_tail_file(path, lines=args.log_tail))
    sections.append("\n".join(["## 3. Logs do serviço", *log_section_lines]))

    # 4. Binário e dependências
    bin_lines: list[str] = []
    resolved_path = exec_path
    if resolved_path:
        bin_lines.append(_format_path(resolved_path))
        if resolved_path.is_symlink():
            bin_lines.append(f"readlink -f: {resolved_path.resolve()}")
        if os.access(resolved_path, os.X_OK):
            bin_lines.append("Permissões de execução OK")
        else:
            bin_lines.append("⚠️ Ficheiro não é executável pelo utilizador atual")
            probable_causes.append("Executável sem permissão de execução")
        bin_lines.append(run_command(["ldd", str(resolved_path)]).format())
        bin_lines.append(_check_virtualenv(resolved_path))
    else:
        bin_lines.append("Não foi possível determinar o executável; a saltar verificações.")
    sections.append("\n".join(["## 4. Binário e dependências", *bin_lines]))

    # 5. Configuração da Unit e Environment
    unit_lines: list[str] = []
    unit_lines.append(run_command(["systemctl", "cat", args.service]).format())
    fragment_path = systemd_props.get("FragmentPath", "")
    fragment_ts = systemd_props.get("FragmentTimestamp", "")
    if fragment_path:
        unit_lines.append(f"FragmentPath: {fragment_path}")
    if fragment_ts:
        unit_lines.append(f"FragmentTimestamp: {fragment_ts}")
    env_files = systemd_props.get("EnvironmentFile", "")
    if env_files:
        unit_lines.append("EnvironmentFile(s) detectados:")
        for entry in env_files.split():
            path = entry.strip().lstrip("-")
            unit_lines.append(_format_path(Path(path)))
            unit_lines.append(_tail_file(Path(path), lines=40))
    if resolved_path and not resolved_path.exists():
        unit_lines.append("⚠️ ExecStart aponta para ficheiro inexistente")
        probable_causes.append("ExecStart aponta para ficheiro inexistente")
    sections.append("\n".join(["## 5. Configuração da Unit e Environment", *unit_lines]))

    # 6. Permissões e utilizadores
    perm_lines: list[str] = []
    _user_exists, user_msg = _check_user_exists(systemd_props.get("User", ""))
    perm_lines.append(user_msg)
    for log_path in args.log_path:
        perm_lines.append(_can_user_write(Path(log_path).parent, systemd_props.get("User", "")))
    for port in args.expected_port:
        if port < 1024:
            perm_lines.append(f"Porta privilegiada detectada (<1024): {port}")
    sections.append("\n".join(["## 6. Permissões e utilizadores", *perm_lines]))

    # 7. Rede
    network_lines: list[str] = []
    listeners, conflicts = _check_expected_ports(args.expected_port)
    if listeners:
        network_lines.append("Portas em escuta:")
        network_lines.extend(listeners)
    if conflicts:
        network_lines.append("Alertas de portas:")
        network_lines.extend(conflicts)
        probable_causes.extend(conflicts)
        recommendations.append("Liberar as portas indicadas ou ajustar a configuração do serviço")
    if args.expected_port:
        for port in args.expected_port:
            result = _test_tcp_connection(args.host, port)
            network_lines.append(f"Teste de ligação a {args.host}:{port} → {result}")
            if result != "Sucesso":
                probable_causes.append(f"Falha na ligação a {args.host}:{port}")
                recommendations.append("Verificar serviço de rede ou firewall")
    network_lines.extend(_collect_firewall_info())
    sections.append("\n".join(["## 7. Rede", *network_lines]))

    # 8. Recursos de sistema
    resources_lines = [
        run_command(["free", "-h"]).format(),
        run_command(["bash", "-lc", "top -bn1 | head -10"]).format()
        if shutil.which("top")
        else "Comando top não disponível",
        run_command(["df", "-h"]).format(),
        run_command(["du", "-sh", "/var/log"]).format(),
        run_command(["uptime"]).format(),
        run_command(["cat", "/proc/loadavg"]).format(),
        run_command(["bash", "-lc", "ulimit -a"]).format(),
    ]
    if args.service:
        resources_lines.append(
            run_command(["systemctl", "show", args.service, "-p", "LimitNOFILE"]).format()
        )
    sections.append("\n".join(["## 8. Recursos de sistema", *resources_lines]))

    # 9. Processos
    process_lines: list[str] = []
    if main_pid and main_pid != "0":
        process_lines.append(run_command(["ps", "-fp", main_pid]).format())
    process_lines.append(
        run_command(["bash", "-lc", f"journalctl -b | grep {shlex.quote(args.service)}"]).format()
    )
    process_lines.append(
        run_command(["bash", "-lc", "ps -eo pid,stat,comm | grep defunct"]).format()
    )
    process_lines.append(run_command(["pgrep", "-fl", args.service]).format())
    sections.append("\n".join(["## 9. Processos", *process_lines]))

    # 10. Segurança / SELinux / AppArmor
    security_lines: list[str] = []
    security_lines.append(run_command(["aa-status"]).format())
    security_lines.append(run_command(["sestatus"]).format())
    security_lines.append(
        run_command(["bash", "-lc", "journalctl -k | grep -i denied"]).format()
    )
    sections.append("\n".join(["## 10. Segurança / SELinux / AppArmor", *security_lines]))

    # 11. Atualizações e pacotes
    updates_lines: list[str] = []
    if args.package:
        updates_lines.append(run_command(["apt", "list", "--installed", args.package]).format())
        updates_lines.append(
            run_command(["bash", "-lc", f"apt-get -s upgrade | grep {shlex.quote(args.package)}"]).format()
        )
    else:
        updates_lines.append("Nenhum pacote específico fornecido para validação.")
    updates_lines.append(run_command(["bash", "-lc", "dpkg -l | grep '^rc'"]).format())
    sections.append("\n".join(["## 11. Atualizações e pacotes", *updates_lines]))

    # 12. Resultado final e resumo
    duration = time.monotonic() - start_monotonic
    state = _get_summary_state(is_active_result)
    if not probable_causes:
        probable_causes.append("Nenhuma causa evidente detectada nos dados recolhidos.")
    if not recommendations:
        recommendations.append("Rever logs detalhados e considerar restart controlado do serviço se apropriado.")
    summary_lines = [
        f"Estado atual: {state}",
        "Causas prováveis:",
    ]
    summary_lines.extend(f"- {cause}" for cause in dict.fromkeys(probable_causes))
    summary_lines.append("Sugestões de ação:")
    summary_lines.extend(f"- {rec}" for rec in dict.fromkeys(recommendations))
    summary_lines.append(
        f"Timestamp final: {datetime.now().isoformat(sep=' ')} — duração total {duration:.1f}s"
    )
    sections.append("\n".join(["## 12. Resultado final e resumo", *summary_lines]))

    return "\n\n".join(sections) + "\n"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="service-diagnostics",
        description="Recolhe diagnóstico completo de um serviço systemd.",
    )
    parser.add_argument("service", help="Nome do serviço systemd (ex.: myapp.service)")
    parser.add_argument(
        "--exec-path",
        help="Caminho do executável a usar caso não seja possível detetar via systemd",
    )
    parser.add_argument(
        "--log-path",
        action="append",
        default=[],
        help="Caminho adicional de log a inspecionar (pode ser usado várias vezes)",
    )
    parser.add_argument(
        "--log-tail",
        type=int,
        default=80,
        help="Número de linhas a recolher de cada log externo (default: 80)",
    )
    parser.add_argument(
        "--journal-lines",
        type=int,
        default=100,
        help="Número de linhas a recolher do journalctl (default: 100)",
    )
    parser.add_argument(
        "--expected-port",
        type=int,
        action="append",
        default=[],
        help="Porta TCP que o serviço deve expor (pode ser usado várias vezes)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host a usar para o teste de ligação TCP (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--package",
        help="Nome do pacote apt associado ao serviço para validações de versão",
    )
    parser.add_argument(
        "--output",
        help="Caminho para guardar o relatório em ficheiro além da saída standard",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    if args.output:
        try:
            Path(args.output).write_text(report, encoding="utf-8")
        except OSError as exc:
            print(f"⚠️ Falha a escrever relatório em {args.output}: {exc}")
    print(report)
    return 0


if __name__ == "__main__":  # pragma: no cover - ponto de entrada manual
    raise SystemExit(main())
