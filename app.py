import os
import requests
import streamlit as st
# sync: ajuste inicial para PR (09-2025)

st.set_page_config(page_title="Painel Letalk", layout="wide", page_icon="💬")
st.title("🔧 Painel Letalk – Bloqueios e Avisos")

# ======= Config: API_BASE por secrets ou env =======
API_BASE = (st.secrets.get("API_BASE")
            or os.environ.get("API_BASE")
            or "https://api-bloqueio-production.up.railway.app").rstrip("/")
st.caption(f"API conectada em: `{API_BASE}`")

# ======= Helpers =======
def parse_ids(raw: str) -> list[str]:
    if not raw: return []
    txt = raw
    for sep in [",", ";", "\n", "\r", "\t", " "]:
        txt = txt.replace(sep, ",")
    out, seen = [], set()
    for i in (x.strip() for x in txt.split(",") if x.strip()):
        if i not in seen:
            seen.add(i); out.append(i)
    return out

def post_api(path: str, payload: dict, timeout=90):
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        ct = r.headers.get("content-type", "")
        data = r.json() if "application/json" in ct else {"raw": r.text}
        return r.status_code, data
    except requests.exceptions.Timeout:
        return 408, {"error": "Timeout ao chamar a API."}
    except requests.exceptions.RequestException as e:
        return 520, {"error": f"Erro de rede: {e}"}
    except Exception as e:
        return 520, {"error": f"Erro inesperado: {e}"}

# ======= Diagnóstico rápido =======
with st.expander("🧪 Diagnóstico de conexão", expanded=True):
    colA, colB = st.columns(2)
    with colA:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=10)
            st.code(f"GET /health -> {r.status_code}\n{r.text[:200]}")
            st.success("Health OK" if r.status_code == 200 else "Health NOK")
        except Exception as e:
            st.error(f"Falha no GET /health: {e}")
    with colB:
        sc, data = post_api("/bloquear", {"instance_ids": []}, timeout=15)
        st.code(f"POST /bloquear (vazio) -> {sc}\n{str(data)[:200]}")
        if sc == 404:
            st.warning("Rota /bloquear não encontrada no back. Confirme a URL/API_BASE.")

# ======= TABS =======
aba_bloqueio, aba_cancelados, aba_avisos = st.tabs([
    "🔒 Bloqueio de Instâncias",
    "🚫 Bloqueio de Cancelados",
    "📢 Avisos"
])

# === BLOQUEIO DE INSTÂNCIAS ===
with aba_bloqueio:
    st.subheader("🔒 Bloquear instâncias por ID")
    raw = st.text_area("IDs (vírgula, espaço ou quebra de linha)", placeholder="Ex: 7618, 7620, 8001")
    ids = parse_ids(raw)
    if ids: st.info(f"Total de IDs: **{len(ids)}**")
    if st.button("🚀 Bloquear Instâncias", disabled=not ids):
        with st.spinner("Processando bloqueio..."):
            sc, data = post_api("/bloquear", {"instance_ids": ids})
        if sc == 200:
            st.success("Bloqueio realizado com sucesso!")
            for log in data.get("log", []):
                st.markdown(f"- {log}")
        else:
            st.error(f"Erro {sc}: {str(data)[:500]}")

# === BLOQUEIO DE CANCELADOS ===
with aba_cancelados:
    st.subheader("🚫 Bloqueio de Cancelados (sem notificação)")
    raw = st.text_area("IDs cancelados", placeholder="Ex: 7618, 7844", key="cancelados")
    ids = parse_ids(raw)
    if ids: st.info(f"Total de IDs: **{len(ids)}**")
    if st.button("🔒 Bloquear Cancelados", disabled=not ids):
        with st.spinner("Bloqueando cancelados..."):
            sc, data = post_api("/bloquear_cancelados", {"instance_ids": ids})
        if sc == 200:
            st.success("Cancelados bloqueados com sucesso!")
            for log in data.get("log", []):
                st.markdown(f"- {log}")
        else:
            st.error(f"Erro {sc}: {str(data)[:500]}")

# === AVISOS ===
with aba_avisos:
    st.subheader("📢 Enviar Avisos para Instâncias")
    raw = st.text_area("IDs para aviso", placeholder="Ex: 7618, 7654", key="avisos")
    ids = parse_ids(raw)
    if ids: st.info(f"Total de IDs: **{len(ids)}**")

    col1, col2, col3, col4 = st.columns(4)

    # EXISTE no back
    if col1.button("📩 Aviso de Bloqueio", disabled=not ids):
        with st.spinner("Enviando aviso de bloqueio..."):
            sc, data = post_api("/avisar_bloqueio", {"instance_ids": ids})
        if sc == 200:
            st.success("Aviso de bloqueio enviado.")
            for log in data.get("log", []):
                st.markdown(f"- {log}")
        else:
            st.error(f"Erro {sc}: {str(data)[:500]}")

    # AINDA NÃO existem no back → desabilitar (ou troque quando criar as rotas)
    col2.button("📆 Aviso de Inadimplência (10 dias)", disabled=True)
    col3.button("⛔ Aviso de Encerramento", disabled=True)

    if col4.button("🔄 Recuperar Cancelamento", disabled=not ids):
        with st.spinner("Enviando solicitação de recuperação..."):
            try:
                r = requests.post(
                    "https://webhook.letalk.com.br/40dcf853-2283-40e5-b71d-d682a6864892",
                    json={"instance_ids": ids}, timeout=60
                )
                if r.status_code == 200:
                    st.success("Recuperação enviada com sucesso!")
                else:
                    st.error(f"Erro no webhook: {r.status_code} – {r.text[:200]}")
            except Exception as e:
                st.error(f"Erro ao chamar webhook: {e}")
