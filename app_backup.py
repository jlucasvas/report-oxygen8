from flask import Flask, render_template, request, send_file, jsonify
import requests
import pdfkit
import json
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

app = Flask(__name__)

# Configuração do pdfkit (certifique-se de ter o wkhtmltopdf instalado)
config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')

# Substitua com as informações da sua instância Metabase
METABASE_URL = "https://bi.besquare.com.br"  # URL do seu Metabase 
# ID da pergunta no Metabase (ajuste conforme seu caso)
CARD_PRODUTO_MAIS_VENDIDO = 95
CARD_TOP_5_PRODUTOS = 96  # Substitua pelo ID correto
CARD_OPERADOR_MAIOR_VENDAS = 97  # Substitua pelo ID correto
CARD_GRAFICO_VENDAS_APOSTAS = 98  # Substitua pelo ID correto
TOKEN = "2ad9ac5a-77d4-40b8-8c33-73ce5b23f503"  # Token obtido na autenticação 


def gerar_grafico_combo(dados):
    # Convertendo dados para DataFrame
    df = pd.DataFrame(dados, columns=['data', 'total_vendido', 'categoria'])
    df['data'] = pd.to_datetime(df['data'])  # Certificando-se de que a coluna 'data' está no formato datetime

    # Configurar a figura
    fig, ax1 = plt.subplots(figsize=(8, 6))

    # Gráfico de barras (Total Vendido)
    ax1.bar(df['data'], df['total_vendido'], color='b', alpha=0.6, label='Total Vendido (R$)')
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Total Vendido (R$)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    # Criar um segundo eixo y para a linha (Categoria)
    ax2 = ax1.twinx()
    ax2.plot(df['data'], df['categoria'], color='g', marker='o', label='Categoria', linestyle='-', linewidth=2)
    ax2.set_ylabel('Apostas', color='g')
    ax2.tick_params(axis='y', labelcolor='g')

    # Formatando eixo x para data
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate()

    # Título do gráfico
    plt.title('Gráfico Combo: Total Vendido x Apostas')

    app_path = os.path.dirname(os.path.abspath(__file__))  # Diretório onde o app.py está localizado
    static_path = os.path.join(app_path,'static', 'grafico_combo.png')  # Caminho completo do arquivo de imagem

    # Salvar o gráfico como imagem
    plt.tight_layout()
    plt.savefig(static_path, format='png')

    plt.close()  # Fechar o gráfico após salvar


def get_metabase_data(card_id, mes, ano):
    try:
        response = requests.post(
            f"{METABASE_URL}/api/card/{card_id}/query",
            headers={"X-Metabase-Session": TOKEN},
            json={
                "parameters": [
                    {
                        "type": "category",
                        "value": f"{mes}/{ano}",
                        "target": ["variable", ["template-tag", "mes_ano"]]
                    }
                ]
            }
        )

        if response.status_code == 202:
            dados = response.json()

            # Verifica se há dados e retorna a primeira linha da resposta
            if "data" in dados and "rows" in dados["data"] and len(dados["data"]["rows"]) > 0:
                return dados["data"]["rows"]
            else:
                print(f"Nenhum dado retornado para o card {card_id}.")
                return None
        else:
            print(f"Erro ao obter dados do Metabase (Card {card_id}): {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Erro ao obter dados do Metabase (Card {card_id}): {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gerar_relatorio', methods=['POST'])
def gerar_relatorio():
    data = request.get_json()
    if not data:
        return jsonify({'erro': 'Dados não recebidos'}), 400

    try:
        mes = int(data.get('mes'))
        ano = int(data.get('ano'))
    except (ValueError, TypeError):
        return jsonify({'erro': 'Parâmetro inválido. Ano e mês devem ser números'}), 400

    if not (1 <= mes <= 12):
        return jsonify({'erro': 'Mês inválido'}), 400

    meses_dict = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    mes_nome = meses_dict.get(mes, "Mês Inválido")

    # Obter dados do Metabase
    produto_mais_vendido = get_metabase_data(CARD_PRODUTO_MAIS_VENDIDO, mes, ano)
    top_5_produtos = get_metabase_data(CARD_TOP_5_PRODUTOS, mes, ano)
    operador_mais_vendas = get_metabase_data(CARD_OPERADOR_MAIOR_VENDAS, mes, ano)
    grafico_vendas_apostas = get_metabase_data(CARD_GRAFICO_VENDAS_APOSTAS, mes, ano)
    gerar_grafico_combo(grafico_vendas_apostas)


    if not produto_mais_vendido or not top_5_produtos or not operador_mais_vendas or not grafico_vendas_apostas:
        return "Erro ao obter dados do Metabase", 500

    # Convertendo os dados do Top 5 produtos para HTML
    produtos_html = "".join(f"<li>{produto[0]} - R$ {produto[1]:,.2f}</li>" for produto in top_5_produtos)

    # Convertendo os dados do gráfico em tabela
    grafico_html = "".join(f"<tr><td>{linha[0]}</td><td>{linha[1]:,.2f}</td><td>{linha[2]}</td></tr>" for linha in grafico_vendas_apostas)

    # Gerar o HTML do relatório
    html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Corporativo</title>
    <style>
        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: Arial, sans-serif;
            font-size: 14px;
            margin: 0;
            padding: 0;
        }}

        .page {{
            position: relative;
            width: 273mm;
            height: 386.1mm;
            background-image: url('http://54.165.210.106:5000/static/imagem.png');
            background-repeat: no-repeat;
            background-position: center;
            background-size: cover; /* Mantém o tamanho original */
            display: flex;
            flex-direction: column;
            justify-content: center; /* Centraliza verticalmente */
            align-items: center; /* Centraliza horizontalmente */
            page-break-after: always;
        }}

        .container {{
            text-align: center;
            width: 100%;
        }}

        h1 {{
            color: #003366;
            font-size: 2.5rem;
        }}

        h2 {{
            color: #003366;
            font-size: 2rem;
            text-align: center;
            margin-top: 30px;
            margin-bottom: 50px;
        }}

        ul {{
            list-style-type: none;
            padding: 0;
            text-align: center;
            font-size: 1.2rem;
            color: #003366;
        }}

        li {{
            margin: 10px 0;
        }}

        .page-number {{
            position: absolute;
            bottom: 20px;
            right: 30px;
            font-size: 12px;
            color: #555;
        }}

        .table {{
                width: 80%;
                border-collapse: collapse;
            }}

        .table, .table th, .table td {{
            border: 1px solid black;
            padding: 8px;
            text-align: left;
            }}
    </style>
</head>
<body>
    <!-- Primeira Página -->
    <div class="page">
        <div class="container">
            <h1>Relatório Corporativo - {mes_nome} {ano}</h1>
        </div>
        <div class="page-number">1</div>
    </div>

    <!-- Segunda Página: Sumário -->
    <div class="page">
        <div class="container">
            <h2>Sumário</h2>
            <ul>
                <li>1. Produto mais vendido .................................. 3</li>
                <li>2. Top 5 Produtos .......................... 4</li>
                <li>3. Operador com mais vendas .............. 5</li>
                <li>4. Análise de Vendas ................................. 6</li>
            </ul>
        </div>
        <div class="page-number">2</div>
    </div>

    <!-- Terceira Página: Produto mais vendido -->
    <div class="page">
        <h2>Produto mais vendido</h2>
        <p>{produto_mais_vendido[0][0]}</p>
        <div class="page-number">3</div>
    </div>

    <!-- Quarta Página: Top 5 Produtos -->
    <div class="page">
        <h2>Top 5 Produtos</h2>
        <ul>
            {produtos_html}
        </ul>
        <div class="page-number">4</div>
    </div>

    <!-- Quinta Página: Operador com maior vendas -->
    <div class="page">
        <h2>Operador com maior número de vendas</h2>
        <p>{operador_mais_vendas[0][0]}</p>
        <div class="page-number">5</div>
    </div>

    <!-- Sexta Página: Tabela de Análise de Vendas -->
    <div class="page">
        <h2>Análise de Vendas</h2>
        <table class="table">
            <tr>
                <th>Data</th>
                <th>Total Vendido (R$)</th>
                <th>Categoria</th>
            </tr>
            {grafico_html}
        </table>
        <div class="page-number">6</div>
    </div>

    <!-- Sétima Página: Gráfico Combo -->
    <div class="page">
        <h2>Gráfico Combo: Total Vendido x Apostas</h2>
        <img src="http://54.165.210.106:5000/static/grafico_combo.png" alt="Gráfico Combo" style="max-width: 100%; height: auto;"/>
        <div class="page-number">7</div>
    </div>

</body>
</html>
"""

    # Gerar PDF
    pdfkit.from_string(html_content, 'relatorio.pdf', configuration=config, options={
        'enable-local-file-access': None
    })

    return send_file('relatorio.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
