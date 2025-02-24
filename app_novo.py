from flask import Flask, render_template, request, send_file, jsonify
import requests
import weasyprint
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns

app = Flask(__name__)

# Substitua com as informações da sua instância Metabase
METABASE_URL = "https://bi.besquare.com.br"  # URL do seu Metabase 
CARD_GGR_RF = 99
CARD_TOTAL_FIN_RF = 100 
CARD_PREMIO_PRESC_RF = 101
CARD_QTD_APOSTAS_RF = 102
CARD_TOTAL_PRIZES_RF = 103
CARD_TOTAL_IR_RF = 104
CARD_REPASSE_EST_RF = 105
CARD_SESSION_COMISSION_RF = 106
CARD_TX_OUTORGA_RF = 107
CARD_QT_OPERADORES_RF = 108
CARD_GR_RECEITA_OPERADOR_RF = 109
CARD_VL_FIN_APOSTAS_RF = 110
CARD_APOSTA_OPERADOR_RF = 111
CARD_RECEITA_LOJA_RF = 112
CARD_APOSTA_LOJA_RF = 113


TOKEN = "2bc69d65-592b-41a9-ba5d-ab69aa3d623b"  # Token obtido na autenticação 


def gerar_grafico_linhas(dados, titulo, filename, xlabel, ylabel):
    # Criando DataFrame com as colunas corretas
    df = pd.DataFrame(dados, columns=["Loja", "Data", ylabel])

    # Convertendo a coluna de data para o formato correto
    df["Data"] = pd.to_datetime(df["Data"])

    # Criando a figura
    plt.figure(figsize=(12, 6))

    # Usando seaborn para gerar um gráfico de linhas automático
    sns.lineplot(data=df, x="Data", y=ylabel, hue="Loja", marker="o", palette="tab10")

    # Configurando título e rótulos dos eixos
    plt.title(titulo)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.7)

    # Salvando o gráfico
    plt.savefig(filename, bbox_inches="tight")
    plt.close()
    return filename



def gerar_grafico_combo(dados):
    df = pd.DataFrame(dados, columns=['started_at', 'sum (R$)', 'sum_2'])
    df['started_at'] = pd.to_datetime(df['started_at'])

    fig, ax1 = plt.subplots(figsize=(8, 6))
    ax1.bar(df['started_at'], df['sum (R$)'], color='b', alpha=0.6, label='Total Líquido (R$)')
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Total Líquido (R$)', color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(df['started_at'], df['sum_2'], color='g', marker='o', label='Apostas', linestyle='-', linewidth=2)
    ax2.set_ylabel('Apostas', color='g')
    ax2.tick_params(axis='y', labelcolor='g')

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    fig.autofmt_xdate()

    plt.title('Total Líquido x Apostas')

    app_path = os.path.dirname(os.path.abspath(__file__))
    static_path = os.path.join(app_path, 'static', 'grafico_combo.png')

    plt.tight_layout()
    plt.savefig(static_path, format='png')
    plt.close()


def gerar_grafico_barras_horizontal(dados, titulo, filename, xlabel, ylabel):
    # Criando o DataFrame corretamente a partir da lista de listas
    df = pd.DataFrame(dados, columns=[ylabel, xlabel])  

    # Ordenando os valores para melhor visualização
    df = df.sort_values(by=xlabel, ascending=True)

    # Criando o gráfico
    plt.figure(figsize=(10, 6))
    plt.barh(df[ylabel], df[xlabel], color="royalblue")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(titulo)
    plt.grid(axis="x", linestyle="--", alpha=0.7)

    # Salvando o gráfico
    plt.savefig(filename, bbox_inches="tight")
    plt.close()
    return filename


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

def formatar_valor(valor, financeiro=False):
    if financeiro:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return f"{valor:,}".replace(",", "X").replace(".", ",").replace("X", ".")

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

    
    dados_total_liq_apostas=get_metabase_data(CARD_VL_FIN_APOSTAS_RF, mes, ano)
    dados_apostas_por_operador=get_metabase_data(CARD_APOSTA_OPERADOR_RF, mes, ano)
    dados_gf_receita_operador=get_metabase_data(CARD_GR_RECEITA_OPERADOR_RF, mes, ano)
    dados_receita_loja=get_metabase_data(CARD_RECEITA_LOJA_RF, mes, ano)
    dados_aposta_loja=get_metabase_data(CARD_APOSTA_LOJA_RF, mes, ano)
    
    indicadores = {
        "ggr": get_metabase_data(CARD_GGR_RF, mes, ano),
        "total_financeiro": get_metabase_data(CARD_TOTAL_FIN_RF, mes, ano),
        "premios_prescritos": get_metabase_data(CARD_PREMIO_PRESC_RF, mes, ano),
        "qtd_apostas": get_metabase_data(CARD_QTD_APOSTAS_RF, mes, ano),
        "total_prizes": get_metabase_data(CARD_TOTAL_PRIZES_RF, mes, ano),
        "total_ir": get_metabase_data(CARD_TOTAL_IR_RF, mes, ano),
        "repasse_estado": get_metabase_data(CARD_REPASSE_EST_RF, mes, ano),
        "session_comission": get_metabase_data(CARD_SESSION_COMISSION_RF, mes, ano),
        "tx_outorga": get_metabase_data(CARD_TX_OUTORGA_RF, mes, ano),
        "qtd_operadores": get_metabase_data(CARD_QT_OPERADORES_RF, mes, ano)
    }

    # Verificar se todos os indicadores foram carregados corretamente
    if any(valor is None for valor in indicadores.values()):
        return "Erro ao obter dados do Metabase", 500


    grafico_receita_operador = gerar_grafico_barras_horizontal(dados_gf_receita_operador, "Receita por Operador", "static/receita_operador.png", "Receita (R$)", "Operador")
    grafico_apostas_operador = gerar_grafico_barras_horizontal(dados_apostas_por_operador, "Apostas por Operador", "static/aposta_operador.png", "Apostas", "Operador")
    grafico_vendas_loja = gerar_grafico_linhas(dados_receita_loja, "Vendas por Loja", "static/vendas_loja.png", "Data", "Vendas")
    grafico_aposta_loja = gerar_grafico_linhas(dados_aposta_loja, "Apostas por Loja", "static/apostas_loja.png", "Data", "Apostas")

    # Criar conteúdo HTML
    with open('templates/relatorio_template.html', 'r', encoding='utf-8') as file:
        html_content = file.read().format(
            mes_nome=mes_nome,
            ano=ano,
            grafico_combo_fin_apostas=gerar_grafico_combo(dados_total_liq_apostas),
            #grafico_apostas_operador=gerar_grafico_barras_horizontal(dados_apostas_por_operador, CARD_APOSTA_OPERADOR_RF),
            #grafico_barras_horizontal=gerar_grafico_barras_horizontal(dados_gf_receita_operador,CARD_GR_RECEITA_OPERADOR_RF),
            **{chave: indicadores[chave][0][0] for chave in indicadores}
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
