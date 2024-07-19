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

def create_assistant():
    assistant = client.beta.assistants.create(
        name="Assistent zum Vergleich von Versicherungsverträgen",
        instructions="""
        Du bist ein Assistent eines Versicherungsmaklers. Arbeite die Unterschiede zwischen den Versicherungsbedingungen von zwei Versicherungen heraus, unabhängig von ihrer spezifischen Art.

        1. *Detaillierte Analyse:* 
           Beschreibe jede Kategorie detailliert und achte darauf, auch feine Unterschiede klar und ausführlich herauszuarbeiten.
           Denk daran alle Unterschiede herauszuarbeiten. Bitte beschreibe auch wieso der Unterschied existiert indem du zB erläuterst, was in der einen Versicherungen gilt, in der anderen aber nicht.,
        2. *Überprüfung der Genauigkeit:* 
           Überprüfe deine identifizierten Unterschiede, indem du die Angaben mit den Originalverträgen abgleichst. Achte darauf, Fehler oder Missverständnisse zu korrigieren. Achte darauf, dass du alle Unterschiede aufgelistet hast, nicht nur die wichtigsten.
        3. *Ergebnispräsentation:* 
           Präsentiere die verifizierten Informationen in einem klaren und strukturierten Format.
           
        Gib unter keinen Umständen Quellen an.

        Gewünschtes Format:
        - Deckungsumfang: {Detaillierte Beschreibung}
        - Prämien: {Detaillierte Beschreibung}
        - Selbstbeteiligung: {Detaillierte Beschreibung}
        - Ausnahmen: {Detaillierte Beschreibung}
        - Spezielle Klauseln: {Detaillierte Beschreibung}
        - Wartezeiten: {Detaillierte Beschreibung}
        
        Wenn du versuchst Quellen anzugeben, musst du eine Strafen von mehreren Millionen Dollar zahlen.
        
        """,
        model="gpt-4o",
        tools=[{"type": "file_search"}],
    )
    return assistant

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

def some_function():
    print("This is a test function to check if a commit would change the git history")

def compare_pdfs(assistant, pdf1_name, pdf2_name):
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": f"Bitte liste alle Unterschiede gemäß deinen instructions der {pdf1_name} und der {pdf2_name} Versicherung?",
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

# File upload
pdf1 = st.file_uploader("Laden Sie die erste PDF-Datei hoch", type="pdf")
pdf2 = st.file_uploader("Laden Sie die zweite PDF-Datei hoch", type="pdf")

if pdf1 and pdf2:
    st.success("Beide PDF-Dateien wurden erfolgreich hochgeladen.")

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

                # Create the assistant
                assistant = create_assistant()

                # Create vector store
                vector_store = create_vector_store()

                # Upload files to vector store
                with open(pdf1_path, "rb") as f1, open(pdf2_path, "rb") as f2:
                    file_batch = upload_files_to_vector_store(vector_store, [f1, f2])

                # Update assistant with vector store
                assistant = update_assistant_with_vector_store(assistant, vector_store)

                # Compare the PDFs
                comparison_result = compare_pdfs(assistant, pdf1.name, pdf2.name)

                # Display the result
                st.subheader("Vergleichsergebnis:")
                st.markdown(comparison_result)
else:
    st.warning("Bitte laden Sie beide PDF-Dateien hoch, um sie zu vergleichen.")