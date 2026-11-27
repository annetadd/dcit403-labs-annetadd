import ast
import operator as op
import requests

OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.USub: op.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    try:
        expr = expression.replace(",", "").strip()
        return str(_eval(ast.parse(expr, mode="eval").body))
    except Exception as e:
        return f"Error: {e}"


def wiki_lookup(title: str) -> str:
    try:
        clean_title = title.strip().replace(" ", "_")
        if not clean_title:
            return "Error: empty page title."
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_title}"
        r = requests.get(url, timeout=10, headers={"User-Agent": "DCIT403-lab"})
        if r.status_code != 200:
            return f"No Wikipedia page found for '{title}'."
        return r.json().get("extract", "")[:800]
    except Exception as e:
        return f"Error looking up '{title}': {e}"


TOOLS = {
    "calculator": calculator,
    "wiki_lookup": wiki_lookup,
}


if __name__ == "__main__":
    print("4*185 + 3*95 ->", calculator("4*185 + 3*95"))
    print("Unsafe input  ->", calculator("__import__('os')"))
    print("Wiki lookup   ->", wiki_lookup("Bono East Region")[:120])