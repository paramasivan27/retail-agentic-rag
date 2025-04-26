import streamlit as st
import requests
import re
import json
import os

from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

PRODUCT_EVENTS_API_URL = os.getenv("PRODUCT_EVENTS_API_URL", "http://product_events_api:8000")
DC_EVENTS_API_URL = os.getenv("DC_EVENTS_API_URL", "http://dc_events_api:8001")
SOH_API_URL = os.getenv("SOH_API_URL", "http://set_stock_on_hand:8002")

def classify_user_intent(user_query: str) -> dict:
    system_prompt = (
        "You are an retail assistant that detects user intent related to retail inventory.\n"
        "Classify the user's message as one of the following intents:\n"
        "- get_stock\n"
        "- set_stock\n"
        "- compare_events\n"
        "- analyze_event\n\n"
        "Note: The user may not say explicitly analyze. Understand if the user is trying to find the reason for an inventory position. \n"
        "If it's 'get_stock' or 'set_stock', extract the SKU and Location ID (and SOH value for set_stock).\n"
        "If it's 'analyze_event', extract product_id and location_type.\n"
        "Reply in JSON like this:\n"
        "{ \"intent\": \"get_stock\", \"sku\": \"30000157\", \"location\": \"3\" }\n"
        "{ \"intent\": \"set_stock\", \"sku\": \"30000157\", \"location\": \"3\", \"soh\": \"100\" }\n"
        "{ \"intent\": \"analyze_event\", \"sku\": \"30000157\", \"loc_type\": \"W\" }"
    )

    response = llm([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query)
    ])

    try:
        return json.loads(response.content.strip())
    except Exception:
        return {"intent": "unknown"}

def get_stock(sku, location):
    try:
        response = requests.get(f"{SOH_API_URL}/get_stock?product_id={sku}&location_id={location}")
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def set_stock(sku, soh, location):
    try:
        payload = {"product_id": int(sku), "soh": int(soh), "location": int(location)}
        response = requests.post(f"{SOH_API_URL}/adjust_stock", json=payload)
        return response.json() if response.status_code == 200 else {"error": response.text}
    except Exception as e:
        return {"error": str(e)}

def fetch_product_events(sku, loc_type=None):
    url = f"{PRODUCT_EVENTS_API_URL}/events?product_id={sku}"
    if loc_type:
        url += f"&loc_type={loc_type}"
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def fetch_dc_events(sku):
    response = requests.get(f"{DC_EVENTS_API_URL}/events?product_id={sku}")
    return response.json() if response.status_code == 200 else None

def main():
    st.title("Retail Events Analyzer")

    user_input = st.text_input("Enter your query here:")

    if st.button("Analyze"):
        result = classify_user_intent(user_input)
        intent = result.get("intent")
        st.write(f"**Detected Intent**: {intent}")

        if intent == "get_stock":
            stock_data = get_stock(result['sku'], result['location'])
            st.subheader("Stock on Hand")
            if isinstance(stock_data, dict):
                st.json(stock_data)
            else:
                st.error("Invalid response format. Expected JSON object.")

        elif intent == "set_stock":
            update_result = set_stock(result['sku'], result['soh'], result['location'])
            st.subheader("Stock Update Result")
            if isinstance(update_result, dict):
                st.json(update_result)
            else:
                st.error("Invalid response format. Expected JSON object.")

        elif intent == "compare_events":
            sku = result.get("sku") or extract_sku_from_query(user_input)
            if sku == "None":
                st.warning("Could not extract SKU from your message.")
                return

            inv_data = fetch_product_events(sku)
            dc_data = fetch_dc_events(sku)

            if not inv_data or not dc_data:
                st.warning("Could not retrieve inventory/DC events data.")
                return

            json_inv = json.dumps(inv_data)
            json_dc = json.dumps(dc_data)

            prompt = (
                f"You are a data assistant that analyzes retail events. Given two data sets (Inventory and DC), "
                f"compare and summarize key differences, especially missing or conflicting events.\n"
                f"Inventory Data: {json_inv}\n"
                f"DC Data: {json_dc}"
            )

            summary = llm([HumanMessage(content=prompt)]).content.strip()
            st.subheader("Summary")
            st.write(summary)

        elif intent == "analyze_event":
            sku = result.get("sku")
            loc_type = result.get("loc_type")
            events = fetch_product_events(sku, loc_type)

            if not events:
                st.warning("No events found for the given product and location type.")
                return

            json_events = json.dumps(events)
            prompt = (
                f"You are a retail assistant that analyzes retail inventory events for a specific location type. "
                f"There are two types of locations S for store and W for wharehouse. \n"
                f"Summarize the key activity, patterns, or anomalies from the following event data:\n"
                f"{json_events}"
            )

            summary = llm([HumanMessage(content=prompt)]).content.strip()
            st.subheader("Event Analysis")
            st.write(summary)

        else:
            st.warning("Intent not understood. Please try again with a clearer query.")

def extract_sku_from_query(query: str) -> str:
    chat = ChatOpenAI(temperature=0, model_name="gpt-4o")
    system_prompt = (
        "You are an assistant that extracts SKU numbers from user text. "
        "If you find an SKU, return only that SKU. If there is no SKU, return 'None'."
    )
    user_prompt = f"User's query: {query}"
    response = chat([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    raw_content = response.content.strip()
    match = re.search(r"\\b\\d+\\b", raw_content)
    return match.group(0) if match else "None"


if __name__ == "__main__":
    main()
