import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

# Access API keys
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

# Define categories
categories = [
    "Deckungsumfang",
    "Versicherungssummen",
    "Prämien und Zahlungsmodalitäten",
    "Selbstbeteiligungen",
    "Ausschlüsse und Einschränkungen",
    "Wartezeiten",
    "Kündigungsfristen und -bedingungen",
    "Zusatzleistungen und Optionen",
    "Besondere Klauseln und Bedingungen",
    "Schadensmeldung und Regulierungsprozess"
]

def generate_instructions(category, doc1_name, doc2_name):
    return f"""
    Du bist ein hochspezialisierter Assistent für den Vergleich von Versicherungsverträgen. Deine Aufgabe ist es, eine gründliche und detaillierte Analyse der Unterschiede zwischen den beiden Versicherungsdokumenten in der Kategorie '{category}' durchzuführen.

    Befolge diese Anweisungen genau:

    Systematische Analyse:
    Gehe beide Dokumente Abschnitt für Abschnitt durch.
    Vergleiche jeden einzelnen Punkt und jede Klausel sorgfältig.
    Achte besonders auf Feinheiten und scheinbar kleine Unterschiede.
    Vollständige Erfassung aller Unterschiede:
    Erfasse ausnahmslos ALLE Unterschiede in der Kategorie '{category}', unabhängig davon, wie klein sie erscheinen mögen.
    Detaillierte Erklärung:
    Beschreibe genau, was in der Versicherung '{doc1_name}' gilt und in der Versicherung '{doc2_name}' nicht gilt.
    Erläutere die möglichen Auswirkungen dieser Unterschiede für den Versicherungsnehmer.
    Strukturierte Darstellung:
    Präsentiere die Ergebnisse in folgendem Format:
    {category}: {{Detaillierte Beschreibung aller Unterschiede}}
    Besondere Betonung der Unterschiede:
    Stelle sicher, dass jede Klausel aus beiden Dokumenten verglichen und die Unterschiede hervorgehoben werden. Gib an, warum diese Unterschiede für den Versicherungsnehmer relevant sind.
    Qualitätssicherung:
    Überprüfe deine Analyse auf Vollständigkeit und Genauigkeit.
    Stelle sicher, dass du keine Unterschiede übersehen hast.
    Bei Unklarheiten oder Widersprüchen in den Dokumenten, weise explizit darauf hin.
    Denk daran: Deine Analyse muss absolut gründlich, präzise und zuverlässig sein. Jeder noch so kleine Unterschied kann für den Versicherungsnehmer von Bedeutung sein.
    """

def generate_user_prompt(category, doc1_name, doc2_name):
    return f"""
    Führe eine detaillierte und strukturierte Analyse der beiden Versicherungsdokumente in der Kategorie '{category}' durch:

    {category}
    a) Beschreibe die Bestimmungen in der Versicherung '{doc1_name}'.
    b) Beschreibe die Bestimmungen in der Versicherung '{doc2_name}'.
    c) Hebe die Unterschiede hervor und erläutere die möglichen Auswirkungen dieser Unterschiede für den Versicherungsnehmer.

    Nach der Analyse:

    Überprüfe deine Analyse auf Vollständigkeit und Konsistenz. Stelle sicher, dass du keine wichtigen Punkte übersehen hast. Führe diese Analyse intern durch. Du musst in deiner Antwort nichts zu Vollstänigkeit und Konsistenz schreiben.
    Wenn es Unklarheiten oder scheinbare Widersprüche in den Dokumenten gibt, weise explizit darauf hin.
    Wichtig: Basiere deine Analyse ausschließlich auf den Informationen in den bereitgestellten Dokumenten. Wenn zu einem Punkt keine Informationen verfügbar sind, gib dies klar an.
    """

@st.cache_resource
def create_assistant(instructions):
    assistant = client.beta.assistants.create(
        name="Assistent zum Vergleich von Versicherungsverträgen",
        instructions=instructions,
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )
    return assistant

@st.cache_resource
def create_vector_store():
    return client.beta.vector_stores.create(name="Versicherungsbedingungen")

def upload_files_to_vector_store(vector_store, files):
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=files
    )
    return file_batch

def update_assistant_with_vector_store(assistant, vector_store):
    return client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
    )

def compare_pdfs(assistant, pdf1_name, pdf2_name, category):
    user_prompt = generate_user_prompt(category, pdf1_name, pdf2_name)
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ]
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant.id
    )
    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
    if not messages:
        return "Keine Nachrichten wurden zurückgegeben. Möglicherweise ist ein Fehler aufgetreten."
    message_content = messages[0].content[0].text
    return message_content.value

st.title("Versicherungsverträge Vergleich")

# Use session state to manage button visibility and comparison status
if 'comparison_done' not in st.session_state:
    st.session_state.comparison_done = False

if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None

if 'pdf1_name' not in st.session_state:
    st.session_state.pdf1_name = None

if 'pdf2_name' not in st.session_state:
    st.session_state.pdf2_name = None

# File upload
pdf1 = st.file_uploader("Laden Sie die erste PDF-Datei hoch", type="pdf")
pdf2 = st.file_uploader("Laden Sie die zweite PDF-Datei hoch", type="pdf")

# Category selection
selected_category = st.selectbox("Wählen Sie eine Kategorie für die Analyse", categories)

# Update session state
if selected_category != st.session_state.selected_category:
    st.session_state.selected_category = selected_category
    st.session_state.comparison_done = False

if pdf1 and pdf2:
    if st.session_state.pdf1_name is None:
        st.session_state.pdf1_name = pdf1.name
    if st.session_state.pdf2_name is None:
        st.session_state.pdf2_name = pdf2.name

    st.success("Beide PDF-Dateien wurden erfolgreich hochgeladen.")

    if not st.session_state.comparison_done:
        if st.button("Vergleichen"):
            with st.spinner("Vergleiche die Versicherungsverträge... Das kann einen Moment dauern"):
                # Create a temporary directory to store the uploaded files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save the uploaded files to the temporary directory
                    pdf1_path = os.path.join(temp_dir, pdf1.name)
                    pdf2_path = os.path.join(temp_dir, pdf2.name)

                    with open(pdf1_path, "wb") as f:
                        f.write(pdf1.getvalue())
                    with open(pdf2_path, "wb") as f:
                        f.write(pdf2.getvalue())

                    # Generate dynamic instructions
                    instructions = generate_instructions(selected_category, pdf1.name, pdf2.name)

                    # Create the assistant
                    assistant = create_assistant(instructions)

                    # Create vector store
                    vector_store = create_vector_store()

                    # Upload files to vector store
                    with open(pdf1_path, "rb") as f1, open(pdf2_path, "rb") as f2:
                        file_batch = upload_files_to_vector_store(vector_store, [f1, f2])

                    # Update assistant with vector store
                    assistant = update_assistant_with_vector_store(assistant, vector_store)

                    # Compare the PDFs
                    comparison_result = compare_pdfs(assistant, pdf1.name, pdf2.name, selected_category)

                    # Display the result
                    st.subheader("Vergleichsergebnis:")
                    st.markdown(comparison_result)

                    # Mark comparison as done
                    st.session_state.comparison_done = True

    if st.session_state.comparison_done:
        if st.button("Weitere Kategorie vergleichen"):
            st.session_state.comparison_done = False
            st.rerun()
else:
    st.warning("Bitte laden Sie beide PDF-Dateien hoch, um sie zu vergleichen.")
