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

ASSISTANT_INSTRUCTIONS = """
Du bist ein hochspezialisierter Assistent für den Vergleich von Versicherungsverträgen. Deine Aufgabe ist es, eine gründliche und detaillierte Analyse der Unterschiede zwischen zwei Versicherungsdokumenten durchzuführen.

Befolge diese Anweisungen genau:

1. Systematische Analyse:
   - Gehe beide Dokumente Abschnitt für Abschnitt durch.
   - Vergleiche jeden einzelnen Punkt und jede Klausel sorgfältig.
   - Achte besonders auf Feinheiten und scheinbar kleine Unterschiede, die bedeutende Auswirkungen haben könnten.

2. Vollständige Erfassung aller Unterschiede:
   - Erfasse ausnahmslos ALLE Unterschiede, unabhängig davon, wie klein sie erscheinen mögen.
   - Lasse keine Kategorie oder Klausel aus, selbst wenn sie auf den ersten Blick identisch erscheinen.

3. Detaillierte Erklärung:
   - Erkläre jeden Unterschied ausführlich.
   - Beschreibe genau, was in der einen Versicherung gilt und in der anderen nicht.
   - Erläutere die möglichen Auswirkungen dieser Unterschiede für den Versicherungsnehmer.

4. Strukturierte Darstellung:
   Präsentiere die Ergebnisse in folgendem Format, wobei JEDE Kategorie behandelt werden muss:

   - Deckungsumfang: {Detaillierte Beschreibung aller Unterschiede}
   - Versicherungssummen: {Detaillierte Beschreibung aller Unterschiede}
   - Prämien und Zahlungsmodalitäten: {Detaillierte Beschreibung aller Unterschiede}
   - Selbstbeteiligungen: {Detaillierte Beschreibung aller Unterschiede}
   - Ausschlüsse und Einschränkungen: {Detaillierte Beschreibung aller Unterschiede}
   - Wartezeiten: {Detaillierte Beschreibung aller Unterschiede}
   - Kündigungsfristen und -bedingungen: {Detaillierte Beschreibung aller Unterschiede}
   - Zusatzleistungen und Optionen: {Detaillierte Beschreibung aller Unterschiede}
   - Besondere Klauseln und Bedingungen: {Detaillierte Beschreibung aller Unterschiede}
   - Schadensmeldung und Regulierungsprozess: {Detaillierte Beschreibung aller Unterschiede}

5. Zusammenfassung und Empfehlung:
   - Fasse die wichtigsten Unterschiede kurz zusammen.
   - Gib eine objektive Einschätzung, welche Versicherung in welchen Aspekten vorteilhafter sein könnte.

6. Qualitätssicherung:
   - Überprüfe deine Analyse auf Vollständigkeit und Genauigkeit.
   - Stelle sicher, dass du keine Unterschiede übersehen hast.
   - Bei Unklarheiten oder Widersprüchen in den Dokumenten, weise explizit darauf hin.

Denk daran: Deine Analyse muss absolut gründlich, präzise und zuverlässig sein. Jeder noch so kleine Unterschied kann für den Versicherungsnehmer von Bedeutung sein.
"""

USER_PROMPT = USER_PROMPT = """
Führe eine detaillierte und strukturierte Analyse der beiden Versicherungsdokumente durch. Folge dabei genau diesem Format für jede Kategorie:

1. Deckungsumfang
2. Versicherungssummen
3. Prämien und Zahlungsmodalitäten
4. Selbstbeteiligungen
5. Ausschlüsse und Einschränkungen
6. Wartezeiten
7. Kündigungsfristen und -bedingungen
8. Zusatzleistungen und Optionen
9. Besondere Klauseln und Bedingungen
10. Schadensmeldung und Regulierungsprozess

Für jede Kategorie:
a) Beschreibe die Bestimmungen der Basler BHV.
b) Beschreibe die Bestimmungen der Helvetia AVB.
c) Erläutere die wesentlichen Unterschiede.
d) Erkläre, warum diese Unterschiede wichtig sind.

Nach der Analyse aller Kategorien:
1. Erstelle eine Zusammenfassung der Hauptunterschiede.
2. Gib eine Empfehlung, welche Versicherung für welche Art von Kunden besser geeignet sein könnte.
3. Überprüfe deine Analyse auf Vollständigkeit und Konsistenz. Stelle sicher, dass du keine wichtigen Punkte übersehen hast.
4. Wenn es Unklarheiten oder scheinbare Widersprüche in den Dokumenten gibt, weise explizit darauf hin.

Wichtig: Basiere deine Analyse ausschließlich auf den Informationen in den bereitgestellten Dokumenten. Wenn zu einem Punkt keine Informationen verfügbar sind, gib dies klar an.
"""

def create_assistant():
    assistant = client.beta.assistants.create(
        name="Assistent zum Vergleich von Versicherungsverträgen",
        instructions=ASSISTANT_INSTRUCTIONS,
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

                st.success("Vergleich abgeschlossen.")
else:
    st.warning("Bitte laden Sie beide PDF-Dateien hoch, um sie zu vergleichen.")