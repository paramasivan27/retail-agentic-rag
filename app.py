import os
import re
import json
import requests
import streamlit as st
from typing import Dict, Optional
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# Initialize the LLM
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

# API endpoints
PRODUCT_EVENTS_API_URL = os.getenv("PRODUCT_EVENTS_API_URL", "http://product_events_api:8000")
DC_EVENTS_API_URL = os.getenv("DC_EVENTS_API_URL", "http://dc_events_api:8001")
SOH_API_URL = os.getenv("SOH_API_URL", "http://set_stock_on_hand:8002")


def classify_user_intent(user_query: str) -> Dict:
    system_prompt = (
        "You are an expert intent classifier and extractor. "
        "Respond with exactly one JSON object, and nothing else.\n\n"
        "Extract:\n"
        "- store_number: 4-digit or null\n"
        "- dc_number: 1-2 digit or null\n"
        "- sku_number: 9-digit or null\n"
        "- soh: integer or null (for set_stock)\n"
        "- location_type: 'S' (store) or 'W' (warehouse/DC) or null\n"
        "Identify intent (one of): get_stock, set_stock, compare_events, "
        "analyze_event for one location, analyze_event for one location type\n\n"
        "Reply in JSON like this::\n"
        "{"
        "\"intent\": <intent>,"
        "\"store_number\": <string|null>,"
        "\"dc_number\": <string|null>,"
        "\"sku_number\": <string|null>,"
        "\"soh\": <integer|null>,"
        "\"location_type\": <\"S\"|\"W\"|null>"
        "}"
    )

    response = llm([SystemMessage(content=system_prompt),
                    HumanMessage(content=user_query)
                    ])
    #st.write(response)
    try:
        raw = response.content.strip()
        # 2) pull out the first {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "intent": "unknown",
                "store_number": None,
                "dc_number": None,
                "sku_number": None,
                "soh": None,
                "location_type": None,
                "reasoning": f"Could not parse JSON from: {raw!r}"
                }
    
    except Exception as e:
        return {
            "intent": "unknown",
            "store_number": None,
            "dc_number": None,
            "sku_number": None,
            "soh": None,
            "location_type": None,
            "reasoning": f"Error parsing response: {e}"
            }

def get_stock(sku: int, location_id: int) -> dict:
    try:
        resp = requests.get(f"{SOH_API_URL}/get_stock?product_id={sku}&location_id={location_id}")
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}

def set_stock(sku: int, soh: int, location_id: int) -> dict:
    try:
        payload = {"product_id": sku, "soh": soh, "location": location_id}
        resp = requests.post(f"{SOH_API_URL}/adjust_stock", json=payload)
        return resp.json() if resp.status_code == 200 else {"error": resp.text}
    except Exception as e:
        return {"error": str(e)}

def fetch_product_events(sku: int, loc_type: Optional[str] = None, location_id: Optional[int] = None) -> Optional[dict]:
    url = f"{PRODUCT_EVENTS_API_URL}/events?product_id={sku}"
    if loc_type:
        url += f"&loc_type={loc_type}"
        #st.write(url)
    if location_id:
        url += f"&location_id={location_id}"
        #st.write(url)
    resp = requests.get(url)
    return resp.json() if resp.status_code == 200 else None

def fetch_dc_events(sku: int) -> Optional[dict]:
    resp = requests.get(f"{DC_EVENTS_API_URL}/events?product_id={sku}")
    return resp.json() if resp.status_code == 200 else None

def main():
    st.title("Retail Wizard")

    user_query = st.text_input("Enter your query here:")

    if st.button("Send"):
        result = classify_user_intent(user_query)
        st.write(result)
        intent = result.get("intent")
        st.write("**Detected Intent:**", intent)
        st.write("_Reasoning:_", result.get("reasoning"))
        # Determine location_id from store vs. DC
        loc_type = result.get("location_type")
        location_id = None
        if loc_type == "S":
            location_id = result.get("store_number")
        elif loc_type == "W":
            location_id = result.get("dc_number")
        
        sku = result.get("sku_number")
        soh = result.get("soh")
        
        if intent == "get_stock":
            if not sku or location_id is None:
                st.warning("Missing SKU or location.")
            else:
                stock = get_stock(int(sku), int(location_id))
                st.subheader("Stock on Hand")
                st.json(stock)
        
        elif intent == "set_stock":
            if not sku or location_id is None or soh is None:
                st.warning("Missing SKU, SOH, or location.")
            else:
                update = set_stock(int(sku), int(soh), int(location_id))
                st.subheader("Stock Update Result")
                st.json(update)
        
        elif intent == "compare_events":
            if not sku:
                st.warning("Missing SKU.")
            else:
                inv = fetch_product_events(int(sku))
                dc = fetch_dc_events(int(sku))
                if not inv or not dc:
                    st.warning("Could not retrieve events data.")
                else:
                    prompt = (
                    "You are a data assistant that analyzes retail events. "
                    "Compare and summarize key differences, especially missing or conflicting events.\n"
                    f"Inventory Data: {json.dumps(inv)}\n"
                    f"DC Data: {json.dumps(dc)}"
                    )
                    summary = llm([HumanMessage(content=prompt)]).content.strip()
                    st.subheader("Comparison Summary")
                    st.write(summary)
        
        elif intent == "analyze_event for one location":
            if not sku or location_id is None:
                st.warning("Missing SKU or specific location.")
            else:
                events = fetch_product_events(int(sku), loc_type, int(location_id))
                if not events:
                    st.warning("No events found.")
                else:
                    prompt = (
                        "You are a retail assistant that analyzes events for a specific location."
                        "Display the events in a table."
                        "Give a breif summary of events.\n"
                        f"Event Data: {json.dumps(events)}"
                        )
                    summary = llm([HumanMessage(content=prompt)]).content.strip()
                    st.subheader("Location Analysis")
                    st.write(summary)

        elif intent == "analyze_event for one location type":
            if not sku or not loc_type:
                st.warning("Missing SKU or location type.")
            else:
                events = fetch_product_events(int(sku), loc_type)
                if not events:
                    st.warning("No events found.")
                else:
                    prompt = (
                        "You are a retail assistant that analyzes events for a location type.\n"
                        f"Event Data: {json.dumps(events)}"
                    )
                    summary = llm([HumanMessage(content=prompt)]).content.strip()
                    st.subheader("Location Type Analysis")
                    st.write(summary)

        else:
            st.warning("Intent not understood. Please try again.")

if __name__ == "__main__":
    main()
