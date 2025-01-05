import streamlit as st
import requests
import re
import json

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage


def extract_sku_from_query(query: str) -> str:
    """
    Uses LangChain's ChatOpenAI to find an SKU in the query.
    Returns the SKU if found, otherwise returns 'None'.
    """

    chat = ChatOpenAI(
        temperature=0, 
        model_name="gpt-4o"
    )

    # Prepare system instructions and user input
    system_prompt = (
        "You are an assistant that extracts SKU numbers from user text. "
        "If you find an SKU, return only that SKU. If there is no SKU, return 'None'."
    )
    user_prompt = f"User's query: {query}"

    # Send the messages to the chat model
    response = chat([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    # The model's reply
    raw_content = response.content.strip()

    # Optional: extract just the numeric part using a regex
    match = re.search(r"\b\d+\b", raw_content)
    return match.group(0) if match else "None"


def fetch_product_events(sku):
    """
    Fetches product events for the given SKU from the Inventory (Warehouse) system.
    """
    url = f"http://product_events_api:8000/events?product_id={sku}&loc_type=W"  # Adjust the URL if needed
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data from API: {response.status_code} - {response.text}")
        return None


def fetch_dc_events(sku):
    """
    Fetches product events for the given SKU from the DC system.
    """
    url = f"http://dc_events_api:8001/events?product_id={sku}"  # Adjust the URL if needed
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data from API: {response.status_code} - {response.text}")
        return None


def main():
    st.title("Retail Events Analyzer")

    st.write("""
    **Instructions**:
    1. Enter a statement about a product SKU (e.g., "The Item 30000913 has a difference between store and DC find out why").
    2. Click **Analyze**.
    3. The app will extract the SKU, fetch data from two APIs (Inventory & DC), compare the events via a GPT model, and display the summary.
    """)

    # Text input: user statement
    user_input = st.text_input("Enter your query here:")

    if st.button("Analyze"):
        # 1. Extract SKU using LLM
        sku = extract_sku_from_query(user_input)
        st.write(f"**Extracted SKU**: {sku}")
        
        # If no SKU, exit early
        if sku == "None":
            st.warning("No SKU was found in the text. Please try another query.")
            return
        
        # 2. Fetch product events (Inventory / W)
        events_data = fetch_product_events(sku)
        st.write("**Inventory Events Data**:")
        st.json(events_data)

        # 3. Fetch DC events
        dc_data = fetch_dc_events(sku)
        st.write("**DC Events Data**:")
        st.json(dc_data)

        # Ensure both data are not None
        if events_data is None or dc_data is None:
            st.warning("Could not retrieve events data. Please check your APIs or SKU.")
            return

        # Convert to JSON strings for passing into the prompt
        json_inv_data = json.dumps(events_data)
        json_dc_data = json.dumps(dc_data)

        # 4. Use a ChatOpenAI (GPT-4 or GPT-3.5, whichever is available) to summarize
        # Note: Make sure you have access to the GPT-4 model if using "gpt-4"
        llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

        prompt = (
            f"You are a data assistant that specializes in analyzing retail events. "
            f"Given the following two sets of data about product events in DC and Inventory system, "
            f"compare and find out issues or missing events. Events can be compared using the event_id field. "
            f"Provide a concise summary.\n"
            f"Inventory Data: {json_inv_data}\n"
            f"DC Data: {json_dc_data}"
        )

        # 5. Get the summary from the LLM
        response = llm([HumanMessage(content=prompt)])
        summary = response.content.strip()

        st.subheader("Summary:")
        st.write(summary)


if __name__ == "__main__":
    main()