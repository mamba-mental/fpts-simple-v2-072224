from flask import Flask, request, jsonify
import PyPDF2
import docx
import os
from jinja2 import Template
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

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
        gap_analysis = perform_gap_analysis(client_profile)
        recommendations = generate_recommendations(client_profile, consumer_primary_tradelines, au_data)
        report = render_report(client_profile, gap_analysis, recommendations)
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
    client_profile = {
        "company_name": "Example Company",
        "credit_utilization": 12,
        "payment_history": 85,
        "avg_account_age": 6,
        "oldest_account_age": 15,
        "public_records": 0,
        "new_credit_inquiries": 3,
        "credit_mix": ["Revolving", "Installment", "Mortgage"]
    }
    return client_profile

def perform_gap_analysis(profile):
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

def calculate_fundability_score(profile):
    score = (
        profile['payment_history'] * 0.35 +
        profile['credit_utilization'] * 0.30 +
        profile['avg_account_age'] * 0.15 +
        profile['credit_mix'] * 0.10 +
        profile['new_credit_inquiries'] * 0.10
    )
    capacity = score * 2000
    return score, capacity

def recommend_tradelines(profile, tradeline_list, min_recommendations=2):
    return tradeline_list[:min_recommendations]

def generate_recommendations(profile, tradeline_list, au_list):
    good_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=2)
    better_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=4)
    best_recommendations = recommend_tradelines(profile, tradeline_list, min_recommendations=6)
    
    au_recommendations = au_list[:2]

    good_score, good_capacity = calculate_fundability_score(profile)
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

def render_report(client_profile, gap_analysis, recommendations):
    html_template = open('templates/report_template.html').read()
    template = Template(html_template)
    rendered_html = template.render(
        profile=client_profile,
        creator_name="Your Name",
        report_date=datetime.today().strftime('%Y-%m-%d'),
        introduction_summary="This report provides a comprehensive evaluation...",
        gap_analysis=gap_analysis,
        recommendations=recommendations
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