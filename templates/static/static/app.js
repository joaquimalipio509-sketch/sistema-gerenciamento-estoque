let usuarioAtual = null;

// Inicialização
document.addEventListener("DOMContentLoaded", async () => {
    const res = await fetch("/api/me");
    if (res.ok) {
        usuarioAtual = await res.json();
        mostrarApp();
    }
});

// Login (UC01)
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const senha = document.getElementById("login-senha").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha })
    });

    const data = await res.json();
    if (res.ok) {
        usuarioAtual = data;
        document.getElementById("login-erro").textContent = "";
        mostrarApp();
    } else {
        document.getElementById("login-erro").textContent = data.erro;
    }
});

document.getElementById("btn-logout").addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    location.reload();
});

function mostrarApp() {
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("app-screen").classList.remove("hidden");
    document.getElementById("user-info").textContent = `${usuarioAtual.nome} (${usuarioAtual.perfil})`;
    montarMenu();
}

function montarMenu() {
    const nav = document.getElementById("menu-nav");
    nav.innerHTML = "";

    const menusPorPerfil = {
        Administrador: [
            { label: "Usuários (UC02)", fn: carregarUsuarios },
            { label: "Fornecedores (UC03)", fn: carregarFornecedores },
            { label: "Categorias e Unidades (UC04)", fn: carregarCategoriasUnidades }
        ],
        Estoquista: [
            { label: "Alertas de Estoque (UC10)", fn: carregarAlertas },
            { label: "Produtos (UC05)", fn: carregarProdutos },
            { label: "Entrada de Lotes (UC06/07)", fn: carregarLotes },
            { label: "Saídas e Baixas (UC08/09)", fn: carregarSaidas }
        ],
        Gerente: [
            { label: "Histórico / Auditoria (UC11)", fn: carregarHistorico },
            { label: "Relatório Financeiro (UC12)", fn: carregarFinanceiro },
            { label: "Ranking de Saídas (UC13)", fn: carregarRankingSaidas }
        ]
    };

    const opcoes = menusPorPerfil[usuarioAtual.perfil] || [];
    opcoes.forEach((op, idx) => {
        const btn = document.createElement("button");
        btn.textContent = op.label;
        btn.onclick = () => {
            document.querySelectorAll("#menu-nav button").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            op.fn();
        };
        nav.appendChild(btn);
        if (idx === 0) btn.click();
    });
}

// --- TELAS DO ADMINISTRADOR ---
async function carregarUsuarios() {
    document.getElementById("page-title").textContent = "Gerenciar Usuários";
    const res = await fetch("/api/usuarios");
    const lista = await res.json();

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <h3>Novo Usuário</h3>
            <form id="form-user" class="form-grid">
                <input type="text" id="u-nome" placeholder="Nome" required>
                <input type="email" id="u-email" placeholder="E-mail" required>
                <input type="password" id="u-senha" placeholder="Senha" required>
                <select id="u-perfil">
                    <option value="Administrador">Administrador</option>
                    <option value="Estoquista">Estoquista</option>
                    <option value="Gerente">Gerente</option>
                </select>
                <button type="submit" class="btn-primary">Cadastrar</button>
            </form>
        </div>
        <div class="card">
            <table>
                <thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Status</th><th>Ação</th></tr></thead>
                <tbody>
                    ${lista.map(u => `
                        <tr>
                            <td>${u.nome}</td><td>${u.email}</td><td>${u.perfil}</td>
                            <td>${u.ativo ? "Ativo" : "Inativo"}</td>
                            <td><button class="btn-sm" onclick="toggleStatus('/api/usuarios/${u.id}/status', carregarUsuarios)">Ativar/Inativar</button></td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById("form-user").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: document.getElementById("u-nome").value,
                email: document.getElementById("u-email").value,
                senha: document.getElementById("u-senha").value,
                perfil: document.getElementById("u-perfil").value
            })
        });
        carregarUsuarios();
    };
}

async function carregarFornecedores() {
    document.getElementById("page-title").textContent = "Gerenciar Fornecedores";
    const res = await fetch("/api/fornecedores");
    const lista = await res.json();

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <form id="form-forn" class="form-grid">
                <input type="text" id="f-nome" placeholder="Razão Social" required>
                <input type="text" id="f-cnpj" placeholder="CNPJ" required>
                <input type="text" id="f-tel" placeholder="Telefone">
                <input type="email" id="f-email" placeholder="E-mail">
                <button type="submit" class="btn-primary">Cadastrar</button>
            </form>
        </div>
        <div class="card">
            <table>
                <thead><tr><th>Nome</th><th>CNPJ</th><th>Telefone</th><th>Status</th><th>Ação</th></tr></thead>
                <tbody>
                    ${lista.map(f => `
                        <tr>
                            <td>${f.nome}</td><td>${f.cnpj}</td><td>${f.telefone}</td>
                            <td>${f.ativo ? "Ativo" : "Inativo"}</td>
                            <td><button class="btn-sm" onclick="toggleStatus('/api/fornecedores/${f.id}/status', carregarFornecedores)">Ativar/Inativar</button></td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById("form-forn").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/fornecedores", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: document.getElementById("f-nome").value,
                cnpj: document.getElementById("f-cnpj").value,
                telefone: document.getElementById("f-tel").value,
                email: document.getElementById("f-email").value
            })
        });
        carregarFornecedores();
    };
}

async function carregarCategoriasUnidades() {
    document.getElementById("page-title").textContent = "Categorias e Unidades de Medida";
    const [cats, unis] = await Promise.all([
        fetch("/api/categorias").then(r => r.json()),
        fetch("/api/unidades").then(r => r.json())
    ]);

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <h3>Nova Categoria</h3>
            <form id="form-cat" class="form-grid">
                <input type="text" id="c-nome" placeholder="Nome da Categoria" required>
                <button type="submit" class="btn-primary">Adicionar</button>
            </form>
            <p><b>Cadastradas:</b> ${cats.map(c => c.nome).join(", ") || "Nenhuma"}</p>
        </div>
        <div class="card">
            <h3>Nova Unidade de Medida</h3>
            <form id="form-uni" class="form-grid">
                <input type="text" id="un-nome" placeholder="Nome (ex: Quilograma)" required>
                <input type="text" id="un-sigla" placeholder="Sigla (ex: KG)" required>
                <button type="submit" class="btn-primary">Adicionar</button>
            </form>
            <p><b>Cadastradas:</b> ${unis.map(u => `${u.nome} (${u.sigla})`).join(", ") || "Nenhuma"}</p>
        </div>
    `;

    document.getElementById("form-cat").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/categorias", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ nome: document.getElementById("c-nome").value })
        });
        carregarCategoriasUnidades();
    };

    document.getElementById("form-uni").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/unidades", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: document.getElementById("un-nome").value,
                sigla: document.getElementById("un-sigla").value
            })
        });
        carregarCategoriasUnidades();
    };
}

// --- TELAS DO ESTOQUISTA ---
async function carregarAlertas() {
    document.getElementById("page-title").textContent = "Alertas de Estoque Crítico";
    const alertas = await fetch("/api/alertas").then(r => r.json());

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            ${alertas.length === 0 ? "<p>Nenhum produto em condição crítica no momento.</p>" : `
                <table>
                    <thead><tr><th>Produto</th><th>Qtd. Atual</th><th>Limite Mínimo</th><th>Status</th></tr></thead>
                    <tbody>
                        ${alertas.map(a => `
                            <tr>
                                <td>${a.nome}</td>
                                <td>${a.quantidade} ${a.sigla}</td>
                                <td>${a.estoque_minimo} ${a.sigla}</td>
                                <td><span class="badge-alerta">Estoque Baixo</span></td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            `}
        </div>
    `;
}

async function carregarProdutos() {
    document.getElementById("page-title").textContent = "Catálogo de Produtos";
    const [prods, cats, unis] = await Promise.all([
        fetch("/api/produtos").then(r => r.json()),
        fetch("/api/categorias").then(r => r.json()),
        fetch("/api/unidades").then(r => r.json())
    ]);

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <form id="form-prod" class="form-grid">
                <input type="text" id="p-nome" placeholder="Nome do Produto" required>
                <select id="p-cat">${cats.map(c => `<option value="${c.id}">${c.nome}</option>`).join("")}</select>
                <select id="p-uni">${unis.map(u => `<option value="${u.id}">${u.sigla}</option>`).join("")}</select>
                <input type="number" id="p-min" placeholder="Estoque Mínimo" required>
                <input type="number" step="0.01" id="p-val" placeholder="Valor Unitário (R$)" required>
                <button type="submit" class="btn-primary">Cadastrar</button>
            </form>
        </div>
        <div class="card">
            <table>
                <thead><tr><th>Produto</th><th>Categoria</th><th>Qtd. Disponível</th><th>Mínimo</th><th>Valor Unit.</th></tr></thead>
                <tbody>
                    ${prods.map(p => `
                        <tr>
                            <td>${p.nome}</td><td>${p.categoria_nome}</td>
                            <td>${p.quantidade} ${p.unidade_sigla}</td>
                            <td>${p.estoque_minimo}</td>
                            <td>R$ ${p.valor_unitario.toFixed(2)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById("form-prod").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/produtos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                nome: document.getElementById("p-nome").value,
                categoria_id: document.getElementById("p-cat").value,
                unidade_id: document.getElementById("p-uni").value,
                estoque_minimo: document.getElementById("p-min").value,
                valor_unitario: document.getElementById("p-val").value
            })
        });
        carregarProdutos();
    };
}

async function carregarLotes() {
    document.getElementById("page-title").textContent = "Entrada e Status de Lotes";
    const [lotes, prods, forns] = await Promise.all([
        fetch("/api/lotes").then(r => r.json()),
        fetch("/api/produtos").then(r => r.json()),
        fetch("/api/fornecedores").then(r => r.json())
    ]);

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <form id="form-lote" class="form-grid">
                <select id="l-prod">${prods.map(p => `<option value="${p.id}">${p.nome}</option>`).join("")}</select>
                <select id="l-forn">${forns.map(f => `<option value="${f.id}">${f.nome}</option>`).join("")}</select>
                <input type="number" id="l-qtd" placeholder="Quantidade" required>
                <button type="submit" class="btn-primary">Registrar Entrada</button>
            </form>
        </div>
        <div class="card">
            <table>
                <thead><tr><th>ID</th><th>Produto</th><th>Fornecedor</th><th>Qtd.</th><th>Status</th><th>Ação</th></tr></thead>
                <tbody>
                    ${lotes.map(l => `
                        <tr>
                            <td>#${l.id}</td><td>${l.produto_nome}</td><td>${l.fornecedor_nome}</td>
                            <td>${l.quantidade}</td><td><b>${l.status}</b></td>
                            <td>
                                ${l.status !== "Arquivado" ? `<button class="btn-sm" onclick="avancarLote(${l.id})">Avançar Etapa</button>` : "Finalizado"}
                            </td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;

    document.getElementById("form-lote").onsubmit = async (e) => {
        e.preventDefault();
        await fetch("/api/lotes", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                produto_id: document.getElementById("l-prod").value,
                fornecedor_id: document.getElementById("l-forn").value,
                quantidade: document.getElementById("l-qtd").value
            })
        });
        carregarLotes();
    };
}

async function avancarLote(id) {
    const res = await fetch(`/api/lotes/${id}/status`, { method: "PATCH" });
    if (!res.ok) alert((await res.json()).erro);
    carregarLotes();
}

async function carregarSaidas() {
    document.getElementById("page-title").textContent = "Registrar Saída ou Baixa Manual";
    const prods = await fetch("/api/produtos").then(r => r.json());

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <form id="form-saida" class="form-grid">
                <select id="s-prod">${prods.map(p => `<option value="${p.id}">${p.nome} (Disp: ${p.quantidade})</option>`).join("")}</select>
                <select id="s-tipo">
                    <option value="SAIDA_VENDA">Venda / Expedição</option>
                    <option value="BAIXA_MANUAL">Baixa Manual (Quebra/Perda)</option>
                </select>
                <input type="number" id="s-qtd" placeholder="Quantidade" required>
                <input type="text" id="s-motivo" placeholder="Motivo" required>
                <button type="submit" class="btn-primary">Confirmar Saída</button>
            </form>
            <p id="s-msg"></p>
        </div>
    `;

    document.getElementById("form-saida").onsubmit = async (e) => {
        e.preventDefault();
        const res = await fetch("/api/saidas", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                produto_id: document.getElementById("s-prod").value,
                tipo: document.getElementById("s-tipo").value,
                quantidade: document.getElementById("s-qtd").value,
                motivo: document.getElementById("s-motivo").value
            })
        });
        const data = await res.json();
        alert(res.ok ? data.mensagem : data.erro);
        carregarSaidas();
    };
}

// --- TELAS DO GERENTE ---
async function carregarHistorico() {
    document.getElementById("page-title").textContent = "Histórico e Auditoria";
    const movs = await fetch("/api/movimentacoes").then(r => r.json());

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <table>
                <thead><tr><th>Data/Hora</th><th>Produto</th><th>Tipo</th><th>Qtd.</th><th>Motivo</th><th>Usuário</th></tr></thead>
                <tbody>
                    ${movs.map(m => `
                        <tr>
                            <td>${m.data_hora}</td><td>${m.produto_nome}</td><td>${m.tipo}</td>
                            <td>${m.quantidade}</td><td>${m.motivo || "-"}</td><td>${m.usuario_nome}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function carregarFinanceiro() {
    document.getElementById("page-title").textContent = "Relatório Financeiro do Estoque";
    const data = await fetch("/api/relatorios/financeiro").then(r => r.json());

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <h2>Capital Imobilizado Total: R$ ${data.total_geral.toFixed(2)}</h2>
            <table>
                <thead><tr><th>Produto</th><th>Qtd.</th><th>Valor Unitário</th><th>Subtotal</th></tr></thead>
                <tbody>
                    ${data.itens.map(i => `
                        <tr>
                            <td>${i.nome}</td><td>${i.quantidade}</td>
                            <td>R$ ${i.valor_unitario.toFixed(2)}</td>
                            <td>R$ ${i.subtotal.toFixed(2)}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function carregarRankingSaidas() {
    document.getElementById("page-title").textContent = "Produtos com Maior e Menor Saída";
    const lista = await fetch("/api/relatorios/saidas").then(r => r.json());

    document.getElementById("page-content").innerHTML = `
        <div class="card">
            <table>
                <thead><tr><th>Posição</th><th>Produto</th><th>Total de Saídas</th></tr></thead>
                <tbody>
                    ${lista.map((item, idx) => `
                        <tr><td>#${idx + 1}</td><td>${item.nome}</td><td>${item.total_saidas}</td></tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

async function toggleStatus(url, callback) {
    await fetch(url, { method: "PATCH" });
    callback();
}