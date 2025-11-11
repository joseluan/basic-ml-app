import os
import sys
from dotenv import load_dotenv
# Adiciona o diretório raiz ao sys.path para encontrar o módulo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# test_main.py
from fastapi.testclient import TestClient
from app import app # Importe a instância do seu aplicativo
from db.engine import get_mongo_collection
# 1. Crie uma instância do TestClient
client = TestClient(app.app)
load_dotenv()


def test_predictions_1():
    """Teste de retorno da classe 'neutral_statement' """
    
    text = "The report states with certainty that the project is on track."
    response = client.post(f"/predict?text={text}")
    print(response.text)
    assert response.status_code == 200
    payload = response.json()
    class_predict = payload['predictions']['confusion-v1']['top_intent']
    assert class_predict == 'neutral_statement'


def test_predictions_2():
    """Teste de retorno da classe 'confusion' """
    
    text = "quem é você?"
    response = client.post(f"/predict?text={text}")

    assert response.status_code == 200
    payload = response.json()
    class_predict = payload['predictions']['confusion-v1']['top_intent']
    assert class_predict == 'confusion'


def test_predictions_3():
    """Teste de retorno da classe 'certainty' """
    
    text = "This is crystal clear to me"
    response = client.post(f"/predict?text={text}")

    assert response.status_code == 200
    payload = response.json()
    class_predict = payload['predictions']['confusion-v1']['top_intent']
    assert class_predict == 'certainty'


def test_salvar_mongo():
    """Teste verificação se estar salvando no mongo """
    
    text = "Texto de teste salvar no mongo"
    response = client.post(f"/predict?text={text}")

    assert response.status_code == 200
    payload = response.json()
    ENV = os.getenv("ENV", "prod").lower()
    collection = get_mongo_collection(f"{ENV.upper()}_intent_logs")
    filtro = {
        "timestamp": payload['timestamp'],
        "text": text
    }
    documento_encontrado = collection.find_one(filtro)
    assert documento_encontrado != None

