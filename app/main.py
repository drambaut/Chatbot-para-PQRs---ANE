import streamlit as st
from google import genai
from docxtpl import DocxTemplate
import datetime
import os
import json
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

st.set_page_config(page_title="ANE - PQRs", layout="wide")
st.title("ANE - PQRs: Asistente de Respuesta")

# ─────────────────────────────────────────────
#  INICIALIZACIÓN DE ESTADOS
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "doc_data" not in st.session_state:
    st.session_state.doc_data = {
        # Destinatario
        "NOMBRE": "",
        "CARGO": "",
        "EMPRESA": "",
        "CIUDAD": "Bogotá D.C.",
        "ASUNTO": "",
        "CUERPO": "",
        "FECHA": datetime.datetime.now().strftime("%d de %B de %Y"),
        # Firmante
        "FIRMANTE_NOMBRE": "",
        "FIRMANTE_CARGO": "",
        "FIRMANTE_AREA": "",
    }

# ─────────────────────────────────────────────
#  SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Eres un experto jurídico de la ANE (Agencia Nacional del Espectro de Colombia).
Tu tarea es ayudar a redactar respuestas formales a PQR (Peticiones, Quejas y Recursos).

Cuando el usuario te dé información, debes:
1. Responder amablemente explicando lo que harás.
2. Redactar un cuerpo de carta profesional y formal en español colombiano.
3. SIEMPRE incluir al final de tu respuesta un bloque JSON con los datos extraídos.

Usa EXACTAMENTE este formato para el JSON (sin texto adicional después). Si falta algún dato, déjalo como cadena vacía "":
JSON_DATA: {"NOMBRE": "...", "CARGO": "...", "EMPRESA": "...", "CIUDAD": "...", "ASUNTO": "...", "CUERPO": "...", "FIRMANTE_NOMBRE": "...", "FIRMANTE_CARGO": "...", "FIRMANTE_AREA": "..."}

Reglas para el campo CUERPO:
- Debe ser el texto completo de la carta, formal y bien redactado, en un solo bloque de texto.
- No incluyas el encabezado, ni el destinatario, ni la firma en el cuerpo, SOLO los párrafos centrales del mensaje.
"""


# ─────────────────────────────────────────────
#  FUNCIÓN DE LLAMADA A GEMINI 2.5 FLASH
# ─────────────────────────────────────────────
def get_ai_response(user_input: str) -> str:
    chat_history = ""
    for msg in st.session_state.messages:
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        content = msg["content"]
        if "JSON_DATA:" in content:
            content = content.split("JSON_DATA:")[0].strip()
        chat_history += f"{role}: {content}\n\n"

    full_prompt = f"{SYSTEM_PROMPT}\n\nHistorial de conversación:\n{chat_history}Usuario: {user_input}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
    )
    return response.text


# ─────────────────────────────────────────────
#  INTERFAZ PRINCIPAL - CHAT
# ─────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat con el Asistente")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            display_content = message["content"]
            if "JSON_DATA:" in display_content:
                display_content = display_content.split("JSON_DATA:")[0].strip()
            st.markdown(display_content)

    if prompt := st.chat_input(
        "Contextualiza al agente..."
    ):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Redactando respuesta..."):
                try:
                    full_res = get_ai_response(prompt)
                except Exception as e:
                    full_res = f"Error al conectar con Gemini: {e}"
                    st.error(full_res)

            if "JSON_DATA:" in full_res:
                text_part, json_raw = full_res.split("JSON_DATA:", 1)
                st.markdown(text_part.strip())
                try:
                    new_data = json.loads(json_raw.strip())
                    for k, v in new_data.items():
                        if v and k in st.session_state.doc_data:
                            st.session_state.doc_data[k] = v
                    st.success("Datos del documento actualizados automáticamente.")
                except json.JSONDecodeError:
                    st.warning("No se pudo parsear el JSON de datos del documento.")
            else:
                st.markdown(full_res)

            st.session_state.messages.append({"role": "assistant", "content": full_res})

# ─────────────────────────────────────────────
#  SIDEBAR - DATOS Y DESCARGA
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("Datos del Documento")
    st.caption("Los campos se llenan automáticamente con el chat. Puedes editarlos manualmente.")

    st.subheader("Destinatario")
    nombre  = st.text_input("Nombre",          value=st.session_state.doc_data["NOMBRE"])
    cargo   = st.text_input("Cargo",           value=st.session_state.doc_data["CARGO"])
    empresa = st.text_input("Empresa/Entidad", value=st.session_state.doc_data["EMPRESA"])
    ciudad  = st.text_input("Ciudad",          value=st.session_state.doc_data["CIUDAD"])
    asunto  = st.text_area("Asunto",           value=st.session_state.doc_data["ASUNTO"], height=80)
    cuerpo  = st.text_area("Cuerpo",           value=st.session_state.doc_data["CUERPO"], height=250)

    st.subheader("Firmante ANE")
    firmante_nombre = st.text_input("Nombre firmante", value=st.session_state.doc_data["FIRMANTE_NOMBRE"])
    firmante_cargo  = st.text_input("Cargo firmante",  value=st.session_state.doc_data["FIRMANTE_CARGO"])
    firmante_area   = st.text_input("Área/Dirección",  value=st.session_state.doc_data["FIRMANTE_AREA"])

    st.divider()

    if st.button("📄 Generar y Descargar Carta", type="primary", use_container_width=True):
        st.session_state.doc_data.update({
            "NOMBRE": nombre, "CARGO": cargo, "EMPRESA": empresa,
            "CIUDAD": ciudad, "ASUNTO": asunto, "CUERPO": cuerpo,
            "FIRMANTE_NOMBRE": firmante_nombre,
            "FIRMANTE_CARGO": firmante_cargo,
            "FIRMANTE_AREA": firmante_area,
        })

        try:
            base_dir = os.path.dirname(os.path.dirname(__file__)) 
            template_path = os.path.join(base_dir, "templates", "plantillaPQR.docx")
            doc = DocxTemplate(template_path)
            doc.render(st.session_state.doc_data)

            output = BytesIO()
            doc.save(output)
            output.seek(0)

            safe_name = nombre.replace(" ", "_") if nombre else "destinatario"
            st.download_button(
                label="📥 DESCARGAR CARTA (.docx)",
                data=output,
                file_name=f"Respuesta_ANE_{safe_name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except FileNotFoundError:
            st.error("No se encontró 'plantillaPQR.docx' en la carpeta del proyecto.")
        except Exception as e:
            st.error(f"Error al generar el documento: {e}")

    st.divider()

    if st.button("🗑️ Nueva conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.doc_data = {
            "NOMBRE": "", "CARGO": "", "EMPRESA": "",
            "CIUDAD": "Bogotá D.C.", "ASUNTO": "", "CUERPO": "",
            "FECHA": datetime.datetime.now().strftime("%d de %B de %Y"),
            "FIRMANTE_NOMBRE": "", "FIRMANTE_CARGO": "", "FIRMANTE_AREA": "",
        }
        st.rerun()
