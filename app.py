import streamlit as st
from langchain.llms import OpenAI
from transformers import pipeline
import requests
import re
import os
import json
import tensorflow as tf


# Set up environment variables (if needed)
os.environ["OPENAI_API_KEY"] = "s1234"  # Replace with your key if using OpenAI

# Function to extract SKU from user query
def extract_sku_from_query(query):
    match = re.search(r'\bSKU[- ]?(\d+)\b', query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

# Function to fetch product events from the API
def fetch_product_events(sku):
    url = f"http://product_event_api:8000/events?product_id={sku}"  # Replace with your actual API URL
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error fetching data from API: {response.status_code} - {response.text}")
        return None

# Function to summarize the JSON response using LLM
def summarize_json_response(json_data, model_type="openai"):
    summary_text = ""
    if model_type == "openai":
        llm = OpenAI(temperature=0.7)
        prompt = f"Summarize the following events data:\n\n{json.dumps(json_data, indent=2)}"
        summary_text = llm(prompt)
    elif model_type == "huggingface":
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        summary_text = summarizer(json.dumps(json_data, indent=2), max_length=150, min_length=40, do_sample=False)[0]['summary_text']
    return summary_text

# Streamlit UI
st.title("Agentic RAG System with Streamlit")
st.markdown("Provide a query containing an SKU to fetch and summarize product events.")

# User input
query = st.text_input("Enter your query:")

if query:
    sku = extract_sku_from_query(query)
    if sku:
        st.write(f"Extracted SKU: {sku}")
        events_data = fetch_product_events(sku)
        if events_data:
            st.write("Fetched Events Data:")
            st.json(events_data)  # Display the fetched JSON data

            # Summarize the events
            model_choice = st.selectbox("Choose a model for summarization:", ["openai", "huggingface"])
            summary = summarize_json_response(events_data, model_type=model_choice)
            st.write("Summary of Events:")
            st.write(summary)
    else:
        st.warning("No SKU found in the query. Please provide a valid SKU.")