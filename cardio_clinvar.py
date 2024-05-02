from flask import Flask
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
from bs4 import BeautifulSoup
from io import BytesIO
import os
import pathlib
import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
#from plotnine import *


clean = pd.read_csv("clinvar_pf_database",delimiter="\t")
genes = pd.read_csv("genes.refSeq", delimiter="\t", escapechar="\\", skipinitialspace=True)
sequences = pd.read_csv("gene-ccds-seq-length-uniprot.txt", delimiter="\t", dtype={'Length': int})

clinical_sign = ["Pathogenic", "Likely pathogenic", "Pathogenic/Likely pathogenic", "Benign", "Benign/Likely benign", "Conflicting classifications of pathogenicity", "Uncertain significance"]

app = Flask(__name__)
app.config['DEBUG'] = True
app.secret_key = "super secret key"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
google_client_id = "your-google-client-id"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback",
    clock_skew_in_seconds=0
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
        clock_skew_in_seconds=0
    )

    print(id_info)

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    session['picture'] = id_info.get("picture")
    session["name"] = id_info.get("given_name")
    return redirect("/dashboard")

@app.route('/google_logout', methods=('GET', 'POST'))
def logout():
    print(session)
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