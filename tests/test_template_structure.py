import json
from pathlib import Path


def test_requisicao_template_has_required_sections():
    template_path = Path("app/reporting/templates/requisicao_base.json")
    data = json.loads(template_path.read_text(encoding="utf-8"))

    assert data["name"].startswith("Requisição")

    doc_elements = data["docElements"]
    band = next(
        (element for element in doc_elements if element.get("elementType") == "band" and element.get("key") == "artigos"),
        None,
    )
    assert band is not None, "Band 'artigos' deve existir para iterar linhas"

    child_contents = {child.get("content") for child in band.get("children", [])}
    assert "${Codigo}" in child_contents
    assert "${Produto}" in child_contents
    assert "${Quantidade}" in child_contents

    footer = [
        element
        for element in doc_elements
        if element.get("elementType") == "text" and "Artigos sem código de barras" in element.get("content", "")
    ]
    assert footer, "Rodapé deve destacar artigos sem código de barras"
