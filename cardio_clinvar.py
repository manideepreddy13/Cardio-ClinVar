from flask import Flask, Response
from flask import session
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from plotnine import ggplot, aes, geom_bar, theme, element_text, geom_text, ggtitle
from plotnine.ggplot import ggsave
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from plotly.io import write_image
import plotly.express as px
from bs4 import BeautifulSoup
from io import BytesIO
import os
import gzip
import shutil
import schedule
import time
from datetime import datetime, timedelta
import pathlib
import requests
import json
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import subprocess
import csv


def search_variant_id(variant_id):
    url = "https://www.ncbi.nlm.nih.gov/clinvar/"

    with requests.Session() as session:
        session.get(url)
        data = {
            'term': variant_id
        }

        response = session.post(url, data=data)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_tag = soup.find('meta', attrs={'name': 'ncbi_uid'})
            if meta_tag['name'] == 'ncbi_uid':
                uid_value = meta_tag['content']

        else:
            return "Failed to fetch webpage"
    return uid_value

#Check if today is thursday
def is_first_tuesday():
    today = datetime.today()
    is_first_tuesday = today.weekday() == 1 and 1 <= today.day <= 7
    print(f"Today is {today.strftime('%Y-%m-%d')} and is_first_tuesday: {is_first_tuesday}")
    return is_first_tuesday

#Send mail to all the users regarding the update
def send_mail():
    df = pd.read_csv('new_entries.csv', delimiter='\t')
    variant_id_counts = df['variant_id'].value_counts()
    top_variant_ids = variant_id_counts.index.tolist()[:5]
    variant_hyperlinks = []

    for variant_id in top_variant_ids:
        hyperlink = search_variant_id(variant_id)
        variant_hyperlinks.append((variant_id, "https://www.ncbi.nlm.nih.gov/clinvar/variation/" + hyperlink + "/"))

    smtp_port = 587                 # Standard secure SMTP port
    smtp_server = "smtp.gmail.com"  # Google SMTP Server

    email_from = "cardioclinvar mail"
    email_list = []

    pswd = "password of the cardioclinvar mail"

    subject = "This month's updates in the Cardio Clinvar"

    for person in email_list:
        # Make the body of the email
        body = f"""
        The following attachment contains about the records are modified from the past month. Please feel free to check the file to look for any changes that have been made in the database.

        The top variants that have undergone a change are:
        <ul>
        """
        # Add variant hyperlinks if provided
        if variant_hyperlinks:
            for variant_id, hyperlink in variant_hyperlinks:
                body += f"<li><a href='{hyperlink}'>{variant_id}</a></li>"
            body += "</ul>"

        # make a MIME object to define parts of the email
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = person
        msg['Subject'] = subject

        # Attach the body of the message
        msg.attach(MIMEText(body, 'html'))

        # Define the file to attach
        filename = "new_entries.csv"

        # Open the file in python as a binary
        attachment= open(filename, 'rb')  # r for read and b for binary

        # Encode as base 64
        attachment_package = MIMEBase('application', 'octet-stream')
        attachment_package.set_payload((attachment).read())
        encoders.encode_base64(attachment_package)
        attachment_package.add_header('Content-Disposition', "attachment; filename= " + filename)
        msg.attach(attachment_package)

        # Cast as string
        text = msg.as_string()

        # Connect with the server
        print("Connecting to server...")
        TIE_server = smtplib.SMTP(smtp_server, smtp_port)
        TIE_server.starttls()
        TIE_server.login(email_from, pswd)
        print("Successfully connected to server")
        print()

        # Send emails to "person" as list is iterated
        print(f"Sending email to: {person}...")
        TIE_server.sendmail(email_from, person, text)
        print(f"Email sent to: {person}")
        print()

    TIE_server.quit()


def download_and_extract():
    url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

    downloaded_file_path = "variant_summary.txt.gz"
    extracted_file_path = "variant_summary.txt"

    # Download the compressed file
    response = requests.get(url, stream=True)
    with open(downloaded_file_path, 'wb') as f:
        shutil.copyfileobj(response.raw, f)

    # Extract the contents of the compressed file
    with gzip.open(downloaded_file_path, 'rb') as f_in:
        with open(extracted_file_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.remove(downloaded_file_path)
    print("New file downloaded and extracted successfully.")


#Prefiltering of the database (no need of arguments as they are already initialized in the perlscript file)
def prefilter():
    prefilter_script_file = 'prefiltering_new.py'
    subprocess.run(['python', prefilter_script_file])




#Detection of differences in the files
def is_update():
    csv1 = pd.read_csv('clinvar_pf_database', delimiter='\t')
    csv2 = pd.read_csv('summary_prefiltered', delimiter='\t')
    csv1['pos_aa'] = csv1['pos_aa'].astype(str)
    csv2['pos_aa'] = csv2['pos_aa'].astype(str)


    merged = pd.merge(csv2, csv1, how='left', indicator=True)

    rows_only_in_csv2 = merged[merged['_merge'] == 'left_only'].copy()
    rows_only_in_csv2.drop(columns='_merge', inplace=True)
    rows_only_in_csv2.to_csv('new_entries.csv', index=False)

    diff_in_csv = 'new_entries.csv'

    with open('new_entries.csv', 'r') as file:
        csv_reader = csv.reader(file)
        row_count = sum(1 for row in csv_reader)

        if(row_count == 1):
            print('No update in file')
        else :
            print('There are updates in the file')
            #send_mail()
            original_file_path = 'summary_prefiltered'
    
    return original_file_path, diff_in_csv

#schedule.every().day.at("00:00").do(lambda: download_and_extract(), prefilter(), is_update() if is_first_tuesday() else None)

#original_file_path = "clinvar_pf_database"
#download_and_extract()
#prefilter()
#original_file_path, diff_in_csv = is_update()

clean = pd.read_csv("clinvar_pf_database",delimiter="\t")
genes = pd.read_csv("genes.refSeq", delimiter="\t", escapechar="\\", skipinitialspace=True)
sequences = pd.read_csv("gene-ccds-seq-length-uniprot.txt", delimiter="\t", dtype={'Length': int})

clinical_sign = ["Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic", "Benign", "Benign/Likely benign", "Conflicting classifications of pathogenicity", "Uncertain significance"]

app = Flask(__name__)
app.config['DEBUG'] = True
app.secret_key = "super secret key"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
google_client_id = "your_google_client_id"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri=""
)


def login_required(func):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)
        else:
            return func()
        
    return wrapper
        

@app.route('/', methods=('GET', 'POST'))
def home_page():
    return render_template('home_page.html')

@app.route('/google_login', methods=('GET', 'POST'))
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    print(session)
    return redirect(authorization_url)

@app.route('/callback', methods=('GET', 'POST'))
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=google_client_id,
        clock_skew_in_seconds=3
    )

    print(id_info)

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    session['picture'] = id_info.get("picture")
    session["name"] = id_info.get("given_name")


    csv_file = 'user_db.csv'

    with open(csv_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['email'] == session["email"]:
                user_exist = True
                print('User already exists')
                break
            else:
                user_exist = False
                print('New user')
                break


    if user_exist == False:
        with open(csv_file, 'a+', newline='') as csvfile:
            fieldnames = ["google_id", "name", "email", "picture", "given_name"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        
        # Check if the file is empty, then write header
            csvfile.seek(0)
            first_char = csvfile.read(1)
            if not first_char:
                writer.writeheader()
        
        # Write user details to CSV
            writer.writerow(session)
    
    return redirect("/dashboard")

@app.route('/google_logout', methods=('GET', 'POST'))
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard', methods=('GET', 'POST'))
def dashb():
    return render_template('dash_new.html', pic = session['picture'], name = session['name'].upper())

def search_gene(gene):
    
    display_query = f'Searching for gene: "{gene}"'
    print(type(clean))

    # Filter data based on gene name
    if gene in genes["gene"].values:
        subset_one = clean[clean["GeneSymbol"].str.contains(str(gene), case=False)]
    else:
        subset_one = clean[clean["PhenotypeList"].str.contains(str(gene), case=False)]

    # Prepare result table
    result_table = subset_one.to_html(classes="table table-striped")

    return display_query, result_table

def plot_variants(cardio_output, column):
    #types = np.unique(clean['Type'])
    #types = pd.DataFrame(np.unique(cardio_output[column]), columns=[column])

    typegene_2 = ','.join(cardio_output[column]).split(',')
    typegene_3 = pd.DataFrame({column: typegene_2})
    typegene_4 = typegene_3[column].astype('category')
    typegene_5 = pd.DataFrame({f'{column}': typegene_4})
    typegene_6 = typegene_5[f'{column}'].value_counts().sort_index()
    typegene_8 = typegene_6.index.tolist()
    typegene_9 = typegene_5[f'{column}'].astype('category')
    typegene_9.cat.set_categories(typegene_8)
    typegene_9_df = pd.DataFrame(typegene_9)


    if len(cardio_output) == 0:
        plot_title = f'Bar plot of {column}'
        plot_type = (ggplot() +
            ggtitle(plot_title) +
            theme(legend_position='none') +
            geom_bar(stat='identity', fill='blue') +
            geom_text(
                aes(label='..count..'),
                stat='count',
                nudge_y=0.125,
                va='bottom'
            ) +
            theme(axis_text_x=element_text(angle=45, hjust=1)))
    else:
        plot_title = f'Bar plot of {column}'
        plot_type = (ggplot(typegene_9_df) +
            ggtitle(plot_title) +
            aes(x=f'{column}') +
            geom_bar() +
            geom_text(
                aes(label='..count..'),
                stat='count',
                nudge_y=0.125,
                va='bottom'
            ) +
            theme(axis_text_x=element_text(angle=45, hjust=1)))
                
    plot_path = f"static/img/plot_{column}.png"
    ggsave(plot_type, plot_path)
    return plot_path

def gene_protein_mapping(cardio_output):
    gene_counts = (cardio_output['GeneSymbol'].str.replace('-','Intergenic').str.split(';').explode().value_counts().head(10))
    plot_gene = go.Bar(x = gene_counts.index, y = gene_counts.values, marker=dict(color='blue'))
    #plot = go.Figure(data=[plot_gene])
    #plot.update_layout(title='Top 10 Genes in ClinVar', xaxis_title='Gene', yaxis_title='Count')
    
    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(plot_gene)
    fig.update_layout(title='Top 10 Genes in ClinVar', xaxis_title='Gene', yaxis_title='Count')

    plot_path = f"static/img/plot_top10_gene.png"
    write_image(fig, plot_path)
    return plot_path

def plot_phenotypes(cardio_output):
    pheno = cardio_output['PhenotypeList'].str.split('|').explode()
    pheno_counts = pheno.value_counts().head(10)

    plot_pheno = go.Bar(x=pheno_counts.index, 
                        y=pheno_counts.values, 
                        marker=dict(color='blue'),
                        text=pheno_counts.values,
                        textposition='auto') 

    fig = make_subplots(rows=1, cols=1)
    fig.add_trace(plot_pheno)
    fig.update_layout(title='Top 10 Phenotypes in ClinVar', xaxis_title='Phenotype', yaxis_title='Count')
    plot_path = f"static/plot_top10_pheno.png"
    write_image(fig, plot_path)
    return plot_path

@app.route('/result', methods=('GET', 'POST'))
def search():
    
    cardio_input = request.form['cardio_input']
    cardio_input = cardio_input.upper()
    print(cardio_input)

    if cardio_input in genes["gene"].values:
        cardio_output = clean[clean["GeneSymbol"].str.contains(str(cardio_input), case=False)]
    else:
        cardio_output = clean[clean["PhenotypeList"].str.contains(str(cardio_input), case=False)]

    plot_var = []

    for col in ['review', 'Type', 'ClinicalSignificance']:
        plot = plot_variants(cardio_output, col)
        plot_var.append(plot)

    plot = gene_protein_mapping(cardio_output)
    plot_var.append(plot)

    plot = plot_phenotypes(cardio_output)
    plot_var.append(plot)


    print(len(cardio_output))
    result_table = cardio_output.to_html(classes="table table-striped")

    

    return render_template('result.html', display_query=cardio_input, result_table=result_table, plot_path = plot_var)

@app.route('/chatcsv')
def chat_csv():
    return render_template('stream.html', name = session['name'].upper())

@app.route('/chatstream', methods=['POST'])
def stream_data():
    try:
        user_message = request.json['content'].strip()
        print(user_message)
        headers = {
            'accept': 'text/event-stream',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer your_chatcsv_token'
        }
        data = {
            'model': 'gpt-4-0613',
            'messages': [
                {'role': 'user', 'content': user_message}
            ],
            'files': [
                'https://raw.githubusercontent.com/manideepreddy13/Cardio-ClinVar/main/clinvar_pf_database'
            ]
        }
        response = requests.post('https://www.chatcsv.co/api/v1/chat', headers=headers, json=data)
        assistant_message = response.text
        print(assistant_message)
        
        return json.dumps({'message': assistant_message})

        
        #for chunk in response.iter_content(chunk_size=1024):
        #    assistant_message += chunk.decode('utf-8')

        #print(assistant_message)

        #return json.dumps({'message': assistant_message})

        

    except Exception as e:
        print(e)
        return json.dumps({'error': str(e)})
