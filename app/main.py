import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd

from core.rag.retriever import gerar_sql_e_consultar


# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(
    page_title="Data Copilot PRF",
    page_icon="📊",
    layout="wide"
)


# =========================
# HEADER
# =========================
st.title("📊 Data Copilot PRF")
st.markdown("Faça perguntas em linguagem natural sobre os acidentes da PRF e receba análises em tempo real.")


# =========================
# SIDEBAR
# =========================
with st.sidebar:

    st.header("⚙️ Configurações")

    mostrar_sql     = st.checkbox("Mostrar SQL gerado",            value=True)
    mostrar_grafico = st.checkbox("Gerar gráfico automático",      value=True)
    mostrar_mapa    = st.checkbox("Gerar mapa (se houver lat/lon)", value=True)

    st.markdown("---")
    st.markdown("### 💡 Exemplos de perguntas")
    st.markdown("""
- Ranking 10 causas de acidentes em SP decrescente
- Top 10 estados com mais acidentes por ano
- Top 10 km com maior índice de acidentes em São José dos Campos
- Quantos acidentes ocorreram por mês em 2025
- Quantidade de acidentes por tipo de acidentes em São José dos Campos                
- Total de mortes por estado
    """)


# =========================
# INPUT DO USUÁRIO
# =========================
pergunta = st.chat_input("Digite sua pergunta...")


# =========================
# EXECUÇÃO PRINCIPAL
# =========================
if pergunta:

    st.chat_message("user").markdown(pergunta)

    with st.spinner("🔎 Gerando SQL e consultando Athena..."):

        sql = None
        df  = None

        try:
            sql, df = gerar_sql_e_consultar(pergunta)
        except Exception as e:
            st.error(f"❌ Erro ao gerar SQL ou consultar Athena: {e}")

        # Só prossegue se ambos vieram com sucesso
        if sql is not None and df is not None:

            # =========================
            # EXIBIR SQL
            # =========================
            if mostrar_sql:
                st.chat_message("ai").markdown("### 🧠 SQL Gerado")
                st.code(sql, language="sql")

            # =========================
            # EXIBIR RESULTADO
            # =========================
            st.markdown("### 📊 Resultado")

            if df.empty:
                st.info("Nenhum resultado encontrado para essa pergunta.")
            else:
                st.dataframe(df, use_container_width=True)
                st.caption(f"📌 {len(df)} linhas retornadas")

                # =========================
                # GRÁFICO AUTOMÁTICO
                # =========================
                if mostrar_grafico:

                    colunas_numericas   = df.select_dtypes(include=["int64", "float64"]).columns
                    colunas_categoricas = df.select_dtypes(include=["object"]).columns

                    if len(colunas_numericas) > 0 and len(colunas_categoricas) > 0:

                        st.markdown("### 📈 Visualização")

                        try:
                            df_plot    = df.set_index(colunas_categoricas[0])
                            serie_plot = df_plot[colunas_numericas[0]]
                            serie_plot = serie_plot.sort_values(ascending=False).head(10)
                            st.bar_chart(serie_plot)
                        except Exception as e:
                            st.info(f"Não foi possível gerar gráfico automaticamente. ({e})")

                # =========================
                # MAPA AUTOMÁTICO
                # =========================
                if mostrar_mapa and {"latitude", "longitude"}.issubset(df.columns):

                    st.markdown("### 🗺️ Mapa de Acidentes")

                    try:
                        df_mapa = df[["latitude", "longitude"]].dropna()
                        if df_mapa.empty:
                            st.info("Sem coordenadas válidas para exibir no mapa.")
                        else:
                            st.map(df_mapa)
                    except Exception as e:
                        st.info(f"Erro ao gerar mapa: {e}")


# =========================
# FOOTER
# =========================
st.markdown("---")
st.markdown("🚀 Projeto de Data Copilot com RAG + Qdrant + Athena + LLM")
