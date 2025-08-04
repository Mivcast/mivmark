import streamlit as st
from docx2pdf import convert
from datetime import date
from docx import Document
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from verificar_acesso import usuario_tem_acesso



def tela_orcamento(dados_empresa):
    # ⚠️ Verificação de acesso: Admin sempre tem acesso total
    email_usuario = st.session_state.get("dados_usuario", {}).get("email", "")
    if email_usuario != "matheus@email.com":
        if not usuario_tem_acesso("orcamento"):
            st.warning("⚠️ Este módulo está disponível apenas para planos pagos.")
            st.stop()

    st.title("🧾 Gerar Orçamento")

    st.subheader("Dados da Empresa")
    col1, col2 = st.columns([1, 3])
    with col1:
        if dados_empresa.get("logo_url"):
            st.image(dados_empresa["logo_url"], width=150)
    with col2:
        st.markdown(f"**{dados_empresa.get('nome_empresa', '')}**")
        st.markdown(f"CNPJ: {dados_empresa.get('cnpj', '')}")
        st.markdown(f"{dados_empresa.get('rua', '')}, {dados_empresa.get('numero', '')}")
        st.markdown(f"Bairro: {dados_empresa.get('bairro', '')}")
        st.markdown(f"{dados_empresa.get('cidade', '')} - CEP: {dados_empresa.get('cep', '')}")

    st.markdown("---")
    st.subheader("Dados do Cliente")
    nome_cliente = st.text_input("Nome do cliente")
    cpf_cnpj_cliente = st.text_input("CPF ou CNPJ do cliente")
    endereco_cliente = st.text_area("Endereço completo do cliente")

    st.markdown("---")
    st.subheader("Produtos ou Serviços")
    produtos = dados_empresa.get("produtos", [])
    lista_itens = []
    qtd_itens = st.number_input("Quantos itens deseja incluir?", min_value=1, max_value=20, step=1, value=1)

    for i in range(qtd_itens):
        st.markdown(f"**Item {i+1}**")
        col1, col2, col3 = st.columns(3)
        with col1:
            nome = st.selectbox("Produto/Serviço", [p['nome'] for p in produtos] + ["Outro"], key=f"produto_{i}")
            if nome == "Outro":
                nome = st.text_input("Digite o nome", key=f"novo_produto_{i}")
        with col2:
            qtd = st.number_input("Quantidade", min_value=1, step=1, key=f"qtd_{i}")
        with col3:
            valor = st.number_input("Valor unitário (R$)", min_value=0.0, step=0.01, key=f"valor_{i}")
        lista_itens.append({"nome": nome, "qtd": qtd, "valor": valor})

    total = sum(item["qtd"] * item["valor"] for item in lista_itens)
    desconto = st.number_input("Desconto (R$)", min_value=0.0, step=0.01)
    total_final = total - desconto

    st.markdown(f"**Total: R$ {total_final:,.2f}**")

    st.markdown("---")
    st.subheader("Informações Complementares")
    data_orcamento = st.date_input("Data do orçamento", value=date.today())
    validade = st.text_input("Prazo de validade do orçamento (ex: 10 dias)")
    prazo_execucao = st.text_input("Prazo para execução do serviço")
    observacoes = st.text_area("Observações adicionais")

    if st.button("💾 Gerar Orçamento (DOCX e PDF)"):
        salvar_orcamento_docx(dados_empresa, nome_cliente, cpf_cnpj_cliente, endereco_cliente,
                              lista_itens, total_final, desconto, data_orcamento,
                              validade, prazo_execucao, observacoes)

    # -----------------------------------
    # Histórico de Orçamentos
    # Histórico de Orçamentos
    st.markdown("---")
    st.subheader("📁 Orçamentos Salvos")

    caminho = os.path.join("data", "clientes", "orcamentos")
    os.makedirs(caminho, exist_ok=True)
    arquivos = sorted(os.listdir(caminho), reverse=True)

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        nome_filtro = st.text_input("🔍 Filtrar por nome do cliente")
    with col2:
        data_filtro = st.date_input("📅 Filtrar por data do orçamento", value=None)

    orcamentos_por_cliente = {}
    for nome_arquivo in arquivos:
        if not (nome_arquivo.endswith(".docx") or nome_arquivo.endswith(".pdf")):
            continue

        nome_base = nome_arquivo.rsplit(".", 1)[0]
        partes = nome_base.split("_")

        if len(partes) >= 4:
            _, empresa, cliente, datahora = partes[:4]
            cliente_id = cliente
            data_str = datahora[:8]  # yyyyMMdd
            data_formatada = f"{data_str[:4]}-{data_str[4:6]}-{data_str[6:]}"
        else:
            cliente_id = "desconhecido"
            data_formatada = "0000-00-00"

        # Aplicar filtros
        passou_nome = not nome_filtro or nome_filtro.lower() in cliente_id.lower()
        passou_data = not data_filtro or data_formatada == data_filtro.strftime("%Y-%m-%d")

        if passou_nome and passou_data:
            orcamentos_por_cliente.setdefault(cliente_id, []).append((nome_arquivo, data_formatada))

    if not orcamentos_por_cliente:
        st.info("Nenhum orçamento encontrado com os filtros atuais.")
    else:
        for cliente, lista in orcamentos_por_cliente.items():
            st.markdown(f"### 👤 Cliente: `{cliente}`")
            for arq, data in sorted(lista, reverse=True):
                ext = arq.split(".")[-1]
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.markdown(f"- 📄 {arq.replace('_', ' ')}  \n🗓 {data}")
                with col2:
                    with open(os.path.join(caminho, arq), "rb") as f:
                        st.download_button(
                            f"⬇️ Baixar {ext.upper()}",
                            data=f,
                            file_name=arq,
                            mime="application/octet-stream",
                            key=f"down_{arq}"
                        )
                with col3:
                    link = f"https://wa.me/?text=Olá!%20Segue%20seu%20orçamento:%20{arq}"
                    st.markdown(f"[📲 Enviar por WhatsApp]({link})")


# -----------------------------------
def salvar_orcamento_docx(empresa, nome_cliente, cpf_cnpj, endereco_cliente,
                          itens, total, desconto, data_orcamento,
                          validade, prazo_execucao, observacoes):
    doc = Document()
    doc.add_heading("ORÇAMENTO", level=1)

    doc.add_paragraph("DADOS DA EMPRESA", style="Heading 2")
    doc.add_paragraph(f"Nome: {empresa.get('nome_empresa', '')}")
    doc.add_paragraph(f"CNPJ: {empresa.get('cnpj', '')}")
    doc.add_paragraph(f"Endereço: {empresa.get('rua', '')}, {empresa.get('numero', '')}, Bairro {empresa.get('bairro', '')}")
    doc.add_paragraph(f"{empresa.get('cidade', '')} - CEP {empresa.get('cep', '')}")

    doc.add_paragraph("\nDADOS DO CLIENTE", style="Heading 2")
    doc.add_paragraph(f"Nome: {nome_cliente}")
    doc.add_paragraph(f"CPF/CNPJ: {cpf_cnpj}")
    doc.add_paragraph(f"Endereço: {endereco_cliente}")

    doc.add_paragraph("\nITENS:", style="Heading 2")
    for item in itens:
        linha = f"{item['qtd']} x {item['nome']} - R$ {item['valor']:.2f} = R$ {item['qtd'] * item['valor']:.2f}"
        doc.add_paragraph(linha)

    doc.add_paragraph(f"\nDesconto: R$ {desconto:.2f}")
    doc.add_paragraph(f"Total Final: R$ {total:.2f}")
    doc.add_paragraph(f"Data do orçamento: {data_orcamento.strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Validade: {validade}")
    doc.add_paragraph(f"Prazo de execução: {prazo_execucao}")
    doc.add_paragraph(f"\nObservações: {observacoes}")

    nome_base = f"orcamento_{nome_cliente.replace(' ', '_').lower()}_{data_orcamento.strftime('%Y%m%d')}"
    caminho = os.path.join("data", "clientes", "orcamentos")
    os.makedirs(caminho, exist_ok=True)

    docx_path = os.path.join(caminho, f"{nome_base}.docx")
    pdf_path = os.path.join(caminho, f"{nome_base}.pdf")

    doc.save(docx_path)

    try:
        convert(docx_path, pdf_path)
    except Exception as e:
        st.warning(f"Erro ao gerar PDF: {e}")

    st.success(f"Orçamento salvo com sucesso.")
    st.download_button("📥 Baixar DOCX", data=open(docx_path, "rb"), file_name=os.path.basename(docx_path))
    if os.path.exists(pdf_path):
        st.download_button("📥 Baixar PDF", data=open(pdf_path, "rb"), file_name=os.path.basename(pdf_path))
