import json
import pdfkit
from docx import Document
from flask import Flask, request, jsonify
import PyPDF2
import docx
import os
from jinja2 import Template
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Version: 1.2.0
# Last Modified: 2024-07-22
# Purpose: Extract client data from user-attached files, perform analysis, and generate downloadable reports.

# Load JSON files
def load_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def calculate_years_from_date(year, month=1):
    start_date = datetime(year, month, 1)
    today = datetime.today()
    return relativedelta(today, start_date).years

def handle_dynamic_values(tradelines):
    for tradeline in tradelines:
        year = tradeline.get('Year', datetime.today().year)
        tradeline['Account_Age'] = calculate_years_from_date(year)
    return tradelines

business_primary_tradelines = handle_dynamic_values(load_json_file('data/business_primary_tradelines.json')['Standard_Tradeline_List'])
consumer_primary_tradelines = handle_dynamic_values(load_json_file('data/consumer_primary_tradelines.json')['Standard_Tradeline_List'])
business_loan_data = load_json_file('data/Business Loan Approval Data.json')
personal_loan_data = load_json_file('data/Personal Loan Approval Amounts.json')
au_data = load_json_file('data/au_Data.json')

@app.route('/')
def index():
    return "Welcome to the Fundability Report Generator!"

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"})
    if file:
        file_path = os.path.join("uploads", file.filename)
        file.save(file_path)
        text_data = extract_text_from_file(file_path)
        client_profile = extract_client_data(text_data)
        consumer_gap_analysis = perform_consumer_gap_analysis(client_profile)
        business_gap_analysis = perform_business_gap_analysis(client_profile)
        consumer_recommendations = generate_consumer_recommendations(client_profile, consumer_primary_tradelines, au_data)
        business_recommendations = generate_business_recommendations(client_profile, business_primary_tradelines)
        report = render_report(client_profile, consumer_gap_analysis, business_gap_analysis, consumer_recommendations, business_recommendations)
        return jsonify({"message": "Data extraction complete", "report": report})
    return jsonify({"error": "File upload failed"})

def extract_text_from_file(file_path):
    if file_path.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfFileReader(file_path)
        text = ""
        for page_num in range(pdf_reader.numPages):
            text += pdf_reader.getPage(page_num).extract_text()
        return text
    elif file_path.endswith('.doc') or file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif file_path.endswith('.txt'):
        with open(file_path, 'r') as file:
            return file.read()
    else:
        return "Unsupported file format."

def extract_client_data(text):
    # Placeholder example for extracting client data from text
    client_profile = {
        "company_name": "",
        "credit_utilization": 0,
        "payment_history": 0,
        "avg_account_age": 0,
        "oldest_account_age": 0,
        "public_records": 0,
        "new_credit_inquiries": 0,
        "credit_mix": [],
        "naics_code": 0,
        "business_age": 0,
        "consumer_average_fico_score": 0
    }
    
    # Example parsing logic
    if "Client Name:" in text:
        client_profile["company_name"] = text.split("Client Name:")[1].split("Company Name:")[0].strip()
    if "Credit Utilization" in text:
        client_profile["credit_utilization"] = int(text.split("Credit Utilization:")[1].split("%")[0].strip())
    if "Payment History" in text:
        client_profile["payment_history"] = int(text.split("Payment History:")[1].split("%")[0].strip())
    if "Average Account Age" in text:
        client_profile["avg_account_age"] = float(text.split("Average Account Age:")[1].split("years")[0].strip())
    if "Oldest Account Age" in text:
        client_profile["oldest_account_age"] = float(text.split("Oldest Account Age:")[1].split("years")[0].strip())
    if "Public Records" in text:
        client_profile["public_records"] = int(text.split("Public Records:")[1].split(" ")[0].strip())
    if "New Credit Inquiries" in text:
        client_profile["new_credit_inquiries"] = int(text.split("New Credit Inquiries:")[1].split(" ")[0].strip())
    if "Credit Mix" in text:
        client_profile["credit_mix"] = text.split("Credit Mix:")[1].split(",")
    if "NAICS Code" in text:
        client_profile["naics_code"] = int(text.split("NAICS Code:")[1].split(" ")[0].strip())
    if "Business Age" in text:
        client_profile["business_age"] = int(text.split("Business Age:")[1].split("years")[0].strip())
    if "Average FICO Score" in text:
        client_profile["consumer_average_fico_score"] = int(text.split("Average FICO Score:")[1].split(" ")[0].strip())
        
    return client_profile

def perform_consumer_gap_analysis(profile):
    gap_analysis = {
        "Credit Utilization": {"Current": profile['credit_utilization'], "Target": "< 10%", "Gap": profile['credit_utilization'] >= 10},
        "Payment History": {"Current": profile['payment_history'], "Target": "100% on-time payments", "Gap": profile['payment_history'] < 100},
        "Average Account Age": {"Current": profile['avg_account_age'], "Target": "10 years", "Gap": profile['avg_account_age'] < 10},
        "Oldest Account Age": {"Current": profile['oldest_account_age'], "Target": "≥ 15 years", "Gap": profile['oldest_account_age'] < 15},
        "Public Records and Inquiries": {"Current": profile['public_records'], "Target": "No public records", "Gap": profile['public_records'] > 0},
        "New Credit Inquiries": {"Current": profile['new_credit_inquiries'], "Target": "≤ 2 per year", "Gap": profile['new_credit_inquiries'] > 2},
        "Credit Mix": {"Current": profile['credit_mix'], "Target": "Every Type", "Gap": not all(credit in profile['credit_mix'] for credit in ['Revolving', 'Installment', 'Mortgage', 'Auto'])},
    }
    return gap_analysis

def perform_business_gap_analysis(profile):
    gap_analysis = {
        "NAICS Code": {"Current": profile['naics_code'], "Target": "Specific low-risk codes", "Gap": profile['naics_code'] not in [541511, 541512]},
        "Credit Utilization": {"Current": profile['credit_utilization'], "Target": "< 10%", "Gap": profile['credit_utilization'] >= 10},
        "Business Age": {"Current": profile['business_age'], "Target": "≥ 5 years", "Gap": profile['business_age'] < 5},
        "Credit Mix": {"Current": profile['credit_mix'], "Target": "Every Type", "Gap": not all(credit in profile['credit_mix'] for credit in ['Revolving', 'Installment', 'Mortgage', 'Auto'])},
        "Consumer Average FICO Score": {"Current": profile['consumer_average_fico_score'], "Target": "≥ 700", "Gap": profile['consumer_average_fico_score'] < 700},
    }
    return gap_analysis

def calculate_consumer_fundability_score(profile):
    score = (
        profile['payment_history'] * 0.35 +
        profile['credit_utilization'] * 0.30 +
        profile['avg_account_age'] * 0.15 +
        profile['credit_mix'] * 0.10 +
        profile['new_credit_inquiries'] * 0.10
    )
    capacity = score * 2000
    return score, capacity

def calculate_business_fundability_score(profile):
    score = (
        profile['naics_code'] * 0.25 +
        profile['credit_utilization'] * 0.25 +
        profile['business_age'] * 0.20 +
        profile['credit_mix'] * 0.10 +
        profile['consumer_average_fico_score'] * 0.20
    )
    capacity = score * 5000  # Business funding capacity might be higher
    return score, capacity

def recommend_tradelines(profile, tradeline_list, min_recommendations=2):
    return tradeline_list[:min_recommendations]

def generate_consumer_recommendations(profile, tradeline_list, au_list):
    good_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=2)
    better_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=4)
    best_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=6)
    
    au_recommendations = au_list[:2]  # Example

    good_score, good_capacity = calculate_consumer_fundability_score(profile)
    better_score, better_capacity = good_score * 1.5, good_capacity * 1.5
    best_score, best_capacity = good_score * 1.75, good_capacity * 1.75

    recommendations = {
        'Good': {
            'Title': 'Good: Essential Improvements',
            'Description': 'Basic improvements that address the most critical gaps with minimal investment.',
            'Tradelines': good_recommendations,
            'AUs': au_recommendations,
            'Fundability_Score': good_score,
            'Estimated_Funding_Capacity': good_capacity
        },
        'Better': {
            'Title': 'Better: Enhanced Improvements',
            'Description': 'Building on essential improvements for a more robust profile.',
            'Tradelines': better_recommendations,
            'AUs': au_recommendations,
            'Fundability_Score': better_score,
            'Estimated_Funding_Capacity': better_capacity
        },
        'Best': {
            'Title': 'Best: Maximum Improvements',
            'Description': 'Comprehensive improvements for maximum funding potential.',
            'Tradelines': best_recommendations,
            'AUs': au_recommendations,
            'Fundability_Score': best_score,
            'Estimated_Funding_Capacity': best_capacity
        }
    }
    return recommendations

def generate_business_recommendations(profile, tradeline_list):
    good_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=2)
    better_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=4)
    best_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=6)

    good_score, good_capacity = calculate_business_fundability_score(profile)
    better_score, better_capacity = good_score * 1.5, good_capacity * 1.5
    best_score, best_capacity = good_score * 1.75, good_capacity * 1.75

    recommendations = {
        'Good': {
            'Title': 'Good: Essential Improvements',
            'Description': 'Basic improvements that address the most critical gaps with minimal investment.',
            'Tradelines': good_recommendations,
            'Fundability_Score': good_score,
            'Estimated_Funding_Capacity': good_capacity
        },
        'Better': {
            'Title': 'Better: Enhanced Improvements',
            'Description': 'Building on essential improvements for a more robust profile.',
            'Tradelines': better_recommendations,
            'Fundability_Score': better_score,
            'Estimated_Funding_Capacity': better_capacity
        },
        'Best': {
            'Title': 'Best: Maximum Improvements',
            'Description': 'Comprehensive improvements for maximum funding potential.',
            'Tradelines': best_recommendations,
            'Fundability_Score': best_score,
            'Estimated_Funding_Capacity': best_capacity
        }
    }
    return recommendations

def render_report(client_profile, consumer_gap_analysis, business_gap_analysis, consumer_recommendations, business_recommendations):
    html_template = open('templates/report_template.html').read()
    template = Template(html_template)
    rendered_html = template.render(
        profile=client_profile,
        creator_name="Your Name",
        report_date=datetime.today().strftime('%Y-%m-%d'),
        introduction_summary="This report provides a comprehensive evaluation...",
        consumer_gap_analysis=consumer_gap_analysis,
        business_gap_analysis=business_gap_analysis,
        consumer_recommendations=consumer_recommendations,
        business_recommendations=business_recommendations
    )

    with open('output/funding_report.html', 'w') as file:
        file.write(rendered_html)

    pdfkit.from_file('output/funding_report.html', 'output/funding_report.pdf')

    html_content = open('output/funding_report.html').read()
    soup = BeautifulSoup(html_content, 'html.parser')

    doc = Document()
    doc.add_heading('Funding Potential & Tradeline Strategy Report', 0)

    for element in soup.body.children:
        if element.name == 'h1':
            doc.add_heading(element.text, level=1)
        elif element.name == 'h2':
            doc.add_heading(element.text, level=2)
        elif element.name == 'h3':
            doc.add_heading(element.text, level=3)
        elif element.name == 'p':
            doc.add_paragraph(element.text)
        elif element.name == 'table':
            table = doc.add_table(rows=1, cols=len(element.find_all('th')))
            hdr_cells = table.rows[0].cells
            for i, th in enumerate(element.find_all('th')):
                hdr_cells[i].text = th.text
            for row in element.find_all('tr')[1:]:
                row_cells = table.add_row().cells
                for i, td in enumerate(row.find_all('td')):
                    row_cells[i].text = td.text

    doc.save('output/funding_report.docx')
    return rendered_html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)