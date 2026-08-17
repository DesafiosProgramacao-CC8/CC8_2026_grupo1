import os

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from core import search as search_service
from core.indexer import Indexador
from storage import persistence

app = Flask(__name__)

indexador = persistence.carregar_indice() or Indexador()

@app.route("/")
def home():
    return render_template("index.html", indexador=indexador)


@app.route("/indexar", methods=["GET", "POST"])
def indexar():

    global indexador

    if request.method == "POST":
        pasta = request.form.get("pasta", "").strip()

        if not pasta:
            flash("Informe o caminho de uma pasta.", "erro")
            return redirect(url_for("indexar"))

        if not os.path.isdir(pasta):
            flash(f"A pasta '{pasta}' não existe ou não é um diretório.", "erro")
            return redirect(url_for("indexar"))

        novo_indexador = Indexador()
        try:
            novo_indexador.indexar_pasta(pasta)
        except NotImplementedError as e:
            flash(
                "A árvore de índice ainda não foi implementada pelo grupo "
                f"(core/trees/*.py). Detalhe técnico: {e}",
                "erro",
            )
            return redirect(url_for("indexar"))

        indexador = novo_indexador
        persistence.salvar_indice(indexador)
        flash(
            f"Indexação concluída: {indexador.total_arquivos} arquivo(s) "
            f"indexado(s) ({indexador.total_imagens} imagem(ns), "
            f"{indexador.total_documentos} documento(s), "
            f"{indexador.total_ignorados} ignorado(s)).",
            "sucesso",
        )
        return redirect(url_for("home"))

    return render_template("indexar.html", indexador=indexador)


@app.route("/buscar")
def buscar():

    termo = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "todos")

    if not termo:
        return redirect(url_for("home"))

    if indexador.pasta_indexada is None:
        return render_template(
            "resultados.html",
            termo=termo,
            tipo=tipo,
            resultados=[],
            erro="Nenhuma pasta foi indexada ainda.",
        )

    try:
        resultados = search_service.buscar(indexador, termo, tipo)
        erro = None
    except NotImplementedError as e:
        resultados = []
        erro = (
            "A árvore de índice ainda não foi implementada pelo grupo "
            f"(core/trees/*.py). Detalhe técnico: {e}"
        )

    return render_template(
        "resultados.html", termo=termo, tipo=tipo, resultados=resultados, erro=erro
    )


@app.route("/arquivo")
def abrir_arquivo():

    caminho = request.args.get("caminho", "")

    if not caminho or not os.path.isfile(caminho):
        abort(404)

    pasta_base = indexador.pasta_indexada
    if pasta_base and not os.path.abspath(caminho).startswith(os.path.abspath(pasta_base)):
        abort(403)

    return send_file(caminho)


if __name__ == "__main__":
    app.run(debug=True)
