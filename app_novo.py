from flask import Flask, render_template, request, send_file, jsonify
import requests
import weasyprint
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

app = Flask(__name__)

# Substitua com as informações da sua instância Metabase
METABASE_URL = "https://bi.besquare.com.br"  # URL do seu Metabase 
CARD_PRODUTO_MAIS_VENDIDO = 95
CARD_TOP_5_PRODUTOS = 96  # Substitua pelo ID correto
CARD_OPERADOR_MAIOR_VENDAS = 97  # Substitua pelo ID correto
CARD_GRAFICO_VENDAS_APOSTAS = 98  # Substitua pelo ID correto
TOKEN = "2ad9ac5a-77d4-40b8-8c33-73ce5b23f503"  # Token obtido na autenticação 

def gerar_grafico_combo(dados):
    df = pd.DataFrame(dados, columns=['data', 'total_vendido', 'categoria'])
    df['data'] = pd.to_datetime(df['data'])

    fig, ax1 = plt.subplots(figsize=(8, 6))
    ax1.bar(df['data'], df['total_vendido'], color='b', alpha=0.6, label='Total Vendido (R$)')
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Total Vendido (R$)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(df['data'], df['categoria'], color='g', marker='o', label='Categoria', linestyle='-', linewidth=2)
    ax2.set_ylabel('Apostas', color='g')
    ax2.tick_params(axis='y', labelcolor='g')

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate()

    plt.title('Gráfico Combo: Total Vendido x Apostas')

    app_path = os.path.dirname(os.path.abspath(__file__))
    static_path = os.path.join(app_path, 'static', 'grafico_combo.png')

    plt.tight_layout()
    plt.savefig(static_path, format='png')
    plt.close()

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

    produtos_html = "".join(f"<li>{produto[0]} - R$ {produto[1]:,.2f}</li>" for produto in top_5_produtos)
    grafico_html = "".join(f"<tr><td>{linha[0]}</td><td>{linha[1]:,.2f}</td><td>{linha[2]}</td></tr>" for linha in grafico_vendas_apostas)

    # Criando conteúdo HTML a partir de um arquivo externo (melhor para legibilidade e manutenção)
    with open('templates/relatorio_template.html', 'r', encoding='utf-8') as file:
        html_content = file.read().format(
            mes_nome=mes_nome,
            ano=ano,
            produto_mais_vendido=produto_mais_vendido[0][0],
            produtos_html=produtos_html,
            operador_mais_vendas=operador_mais_vendas[0][0],
            grafico_html=grafico_html
        )

    # Gerar PDF com WeasyPrint
    pdf = weasyprint.HTML(string=html_content).write_pdf()

    # Salvar o PDF
    pdf_path = 'relatorio.pdf'
    with open(pdf_path, 'wb') as f:
        f.write(pdf)

    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
