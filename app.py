# -*- coding: utf-8 -*-

import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "chave-secreta-sistema-estoque"  # Em produção, use variável de ambiente
DB_NAME = "estoque.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK(perfil IN ('Administrador', 'Estoquista', 'Gerente')),
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            telefone TEXT,
            email TEXT,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS unidades_medida (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sigla TEXT UNIQUE NOT NULL,
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria_id INTEGER NOT NULL,
            unidade_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 0,
            estoque_minimo INTEGER DEFAULT 5,
            valor_unitario REAL NOT NULL,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (unidade_id) REFERENCES unidades_medida(id)
        );

        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente' CHECK(status IN ('Pendente', 'Em Conferência', 'Armazenado', 'Arquivado')),
            data_entrada TEXT NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA', 'SAIDA_VENDA', 'BAIXA_MANUAL')),
            quantidade INTEGER NOT NULL,
            motivo TEXT,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
    """)

    # Seed inicial de usuários para facilitar os testes
    usuarios_padrao = [
        ("Admin Sistema", "admin@estoque.com", generate_password_hash("123456"), "Administrador"),
        ("João Estoquista", "estoquista@estoque.com", generate_password_hash("123456"), "Estoquista"),
        ("Maria Gerente", "gerente@estoque.com", generate_password_hash("123456"), "Gerente"),
    ]
    for nome, email, senha, perfil in usuarios_padrao:
        cursor.execute(
            "INSERT OR IGNORE INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
            (nome, email, senha, perfil),
        )

    conn.commit()
    conn.close()


# --- Decoradores de Autenticação e Perfil (UC01) ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"erro": "Autenticação necessária."}), 401
        return f(*args, **kwargs)
    return decorated


def perfil_required(perfis):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"erro": "Autenticação necessária."}), 401
            if session.get("perfil") not in perfis:
                return jsonify({"erro": "Acesso negado para o seu perfil."}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.route("/")
def index():
    return render_template("index.html")


# --- UC01: Autenticação ---
@app.route("/api/login", methods=["POST"])
def login():
    dados = request.json
    email = dados.get("email")
    senha = dados.get("senha")

    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["senha"], senha):
        return jsonify({"erro": "Credenciais inválidas."}), 401
    if user["ativo"] == 0:
        return jsonify({"erro": "Conta inativa. Contate o administrador."}), 403

    session["user_id"] = user["id"]
    session["nome"] = user["nome"]
    session["perfil"] = user["perfil"]

    return jsonify({
        "id": user["id"],
        "nome": user["nome"],
        "perfil": user["perfil"]
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"mensagem": "Logout realizado."})


@app.route("/api/me", methods=["GET"])
@login_required
def me():
    return jsonify({
        "id": session["user_id"],
        "nome": session["nome"],
        "perfil": session["perfil"]
    })


# --- UC02: Gerenciar Usuários (Administrador) ---
@app.route("/api/usuarios", methods=["GET", "POST"])
@perfil_required(["Administrador"])
def usuarios():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT id, nome, email, perfil, ativo FROM usuarios").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    dados = request.json
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
            (dados["nome"], dados["email"], generate_password_hash(dados["senha"]), dados["perfil"]),
        )
        conn.commit()
        return jsonify({"mensagem": "Usuário cadastrado com sucesso."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "E-mail já cadastrado."}), 400
    finally:
        conn.close()


@app.route("/api/usuarios/<int:id>/status", methods=["PATCH"])
@perfil_required(["Administrador"])
def toggle_usuario(id):
    conn = get_db()
    conn.execute("UPDATE usuarios SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Status do usuário atualizado."})


# --- UC03: Gerenciar Fornecedores (Administrador) ---
@app.route("/api/fornecedores", methods=["GET", "POST"])
@login_required
def fornecedores():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM fornecedores").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if session.get("perfil") != "Administrador":
        conn.close()
        return jsonify({"erro": "Acesso negado."}), 403

    dados = request.json
    try:
        conn.execute(
            "INSERT INTO fornecedores (nome, cnpj, telefone, email) VALUES (?, ?, ?, ?)",
            (dados["nome"], dados["cnpj"], dados.get("telefone", ""), dados.get("email", "")),
        )
        conn.commit()
        return jsonify({"mensagem": "Fornecedor cadastrado."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "CNPJ já cadastrado."}), 400
    finally:
        conn.close()


@app.route("/api/fornecedores/<int:id>/status", methods=["PATCH"])
@perfil_required(["Administrador"])
def toggle_fornecedor(id):
    conn = get_db()
    conn.execute("UPDATE fornecedores SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Status do fornecedor atualizado."})


# --- UC04: Gerenciar Categorias e Unidades (Administrador) ---
@app.route("/api/categorias", methods=["GET", "POST"])
@login_required
def categorias():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM categorias").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if session.get("perfil") != "Administrador":
        conn.close()
        return jsonify({"erro": "Acesso negado."}), 403

    dados = request.json
    try:
        conn.execute("INSERT INTO categorias (nome) VALUES (?)", (dados["nome"],))
        conn.commit()
        return jsonify({"mensagem": "Categoria cadastrada."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Categoria já existe."}), 400
    finally:
        conn.close()


@app.route("/api/unidades", methods=["GET", "POST"])
@login_required
def unidades():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("SELECT * FROM unidades_medida").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if session.get("perfil") != "Administrador":
        conn.close()
        return jsonify({"erro": "Acesso negado."}), 403

    dados = request.json
    try:
        conn.execute("INSERT INTO unidades_medida (nome, sigla) VALUES (?, ?)", (dados["nome"], dados["sigla"]))
        conn.commit()
        return jsonify({"mensagem": "Unidade cadastrada."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Sigla já existe."}), 400
    finally:
        conn.close()


# --- UC05: Gerenciar Produtos (Estoquista) ---
@app.route("/api/produtos", methods=["GET", "POST"])
@login_required
def produtos():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("""
            SELECT p.*, c.nome AS categoria_nome, u.sigla AS unidade_sigla
            FROM produtos p
            JOIN categorias c ON p.categoria_id = c.id
            JOIN unidades_medida u ON p.unidade_id = u.id
        """).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    if session.get("perfil") != "Estoquista":
        conn.close()
        return jsonify({"erro": "Apenas estoquistas podem cadastrar produtos."}), 403

    dados = request.json
    conn.execute(
        """INSERT INTO produtos (nome, categoria_id, unidade_id, estoque_minimo, valor_unitario)
           VALUES (?, ?, ?, ?, ?)""",
        (dados["nome"], dados["categoria_id"], dados["unidade_id"], dados["estoque_minimo"], dados["valor_unitario"]),
    )
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Produto cadastrado com sucesso."}), 201


# --- UC06 e UC07: Lotes e Ciclo de Vida (Estoquista) ---
@app.route("/api/lotes", methods=["GET", "POST"])
@perfil_required(["Estoquista"])
def lotes():
    conn = get_db()
    if request.method == "GET":
        rows = conn.execute("""
            SELECT l.*, p.nome AS produto_nome, f.nome AS fornecedor_nome
            FROM lotes l
            JOIN produtos p ON l.produto_id = p.id
            JOIN fornecedores f ON l.fornecedor_id = f.id
            ORDER BY l.id DESC
        """).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])

    dados = request.json
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO lotes (produto_id, fornecedor_id, quantidade, status, data_entrada) VALUES (?, ?, ?, 'Pendente', ?)",
        (dados["produto_id"], dados["fornecedor_id"], dados["quantidade"], agora),
    )
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Entrada de lote registrada com status Pendente."}), 201


@app.route("/api/lotes/<int:id>/status", methods=["PATCH"])
@perfil_required(["Estoquista"])
def atualizar_status_lote(id):
    transicoes_validas = {
        "Pendente": "Em Conferência",
        "Em Conferência": "Armazenado",
        "Armazenado": "Arquivado",
    }
    conn = get_db()
    lote = conn.execute("SELECT * FROM lotes WHERE id = ?", (id,)).fetchone()
    if not lote:
        conn.close()
        return jsonify({"erro": "Lote não encontrado."}), 404

    proximo_status = transicoes_validas.get(lote["status"])
    if not proximo_status:
        conn.close()
        return jsonify({"erro": "Transição de status não permitida."}), 400

    conn.execute("UPDATE lotes SET status = ? WHERE id = ?", (proximo_status, id))

    # Ao armazenar o lote, atualiza o estoque disponível e registra movimentação
    if proximo_status == "Armazenado":
        conn.execute("UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?", (lote["quantidade"], lote["produto_id"]))
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, motivo, data_hora) VALUES (?, ?, 'ENTRADA', ?, ?, ?)",
            (lote["produto_id"], session["user_id"], lote["quantidade"], f"Armazenamento do Lote #{id}", agora),
        )

    conn.commit()
    conn.close()
    return jsonify({"mensagem": f"Status atualizado para {proximo_status}."})


# --- UC08 e UC09: Saídas e Baixas Manuais (Estoquista) ---
@app.route("/api/saidas", methods=["POST"])
@perfil_required(["Estoquista"])
def registrar_saida():
    dados = request.json
    produto_id = dados["produto_id"]
    quantidade = int(dados["quantidade"])
    tipo = dados["tipo"]  # 'SAIDA_VENDA' ou 'BAIXA_MANUAL'
    motivo = dados.get("motivo", "")

    if quantidade <= 0:
        return jsonify({"erro": "Quantidade deve ser maior que zero."}), 400

    conn = get_db()
    produto = conn.execute("SELECT quantidade FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not produto:
        conn.close()
        return jsonify({"erro": "Produto não encontrado."}), 404

    if produto["quantidade"] < quantidade:
        conn.close()
        return jsonify({"erro": "Quantidade solicitada superior ao estoque disponível."}), 400

    conn.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?", (quantidade, produto_id))
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO movimentacoes (produto_id, usuario_id, tipo, quantidade, motivo, data_hora) VALUES (?, ?, ?, ?, ?, ?)",
        (produto_id, session["user_id"], tipo, quantidade, motivo, agora),
    )
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Saída registrada com sucesso."}), 201


# --- UC10: Alertas de Estoque Crítico (Estoquista) ---
@app.route("/api/alertas", methods=["GET"])
@perfil_required(["Estoquista", "Gerente"])
def alertas_estoque():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.nome, p.quantidade, p.estoque_minimo, u.sigla
        FROM produtos p
        JOIN unidades_medida u ON p.unidade_id = u.id
        WHERE p.quantidade <= p.estoque_minimo AND p.ativo = 1
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# --- UC11: Histórico e Auditoria (Gerente) ---
@app.route("/api/movimentacoes", methods=["GET"])
@perfil_required(["Gerente"])
def historico_movimentacoes():
    tipo = request.args.get("tipo", "")
    conn = get_db()
    query = """
        SELECT m.*, p.nome AS produto_nome, u.nome AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        JOIN usuarios u ON m.usuario_id = u.id
    """
    params = []
    if tipo:
        query += " WHERE m.tipo = ?"
        params.append(tipo)
    query += " ORDER BY m.id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# --- UC12: Relatório Financeiro do Estoque (Gerente) ---
@app.route("/api/relatorios/financeiro", methods=["GET"])
@perfil_required(["Gerente"])
def relatorio_financeiro():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, nome, quantidade, valor_unitario, (quantidade * valor_unitario) AS subtotal
        FROM produtos WHERE ativo = 1
    """).fetchall()
    conn.close()

    itens = [dict(r) for r in rows]
    total_geral = sum(item["subtotal"] for item in itens)
    return jsonify({"itens": itens, "total_geral": total_geral})


# --- UC13: Relatório de Produtos com Maior e Menor Saída (Gerente) ---
@app.route("/api/relatorios/saidas", methods=["GET"])
@perfil_required(["Gerente"])
def relatorio_saidas():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.id, p.nome, COALESCE(SUM(m.quantidade), 0) AS total_saidas
        FROM produtos p
        LEFT JOIN movimentacoes m ON p.id = m.produto_id AND m.tipo IN ('SAIDA_VENDA', 'BAIXA_MANUAL')
        GROUP BY p.id, p.nome
        ORDER BY total_saidas DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)