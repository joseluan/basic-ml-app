import pytest
import os
import sys
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Adiciona o diretório raiz do projeto ao path para que as importações funcionem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class MockIntentClassifier:
    """Simula a classe IntentClassifier sem carregar arquivos .keras."""
    def __init__(self, load_model=None):
        pass # Não faz nada no init
        
    def predict(self, text: str):
        # Mapeia a entrada para uma saída previsível para o teste
        if "on track" in text:
            return "neutral_statement", {"neutral_statement": 0.95, "confusion": 0.05}
        if "quem é" in text:
            return "confusion", {"neutral_statement": 0.1, "confusion": 0.9}
        if "crystal clear" in text:
            return "certainty", {"neutral_statement": 0.1, "certainty": 0.9}
        return "default_intent", {"default_intent": 1.0}


# 2. Mock do MongoDB Collection: Simula as operações de banco de dados
mock_collection = MagicMock()
# Configura o mock para retornar um valor previsível em insert_one

# 2. Mock do MongoDB Collection: Simula as operações de banco de dados
mock_collection = MagicMock()
# Configura o mock para retornar um valor previsível em insert_one
dados_fic = {"_id":{"$oid":"690bd9f74bcc955c861d06ef"},"text":"UEPA","owner":"dev_user","predictions":{"confusion-v1":{"top_intent":"neutral_statement","all_probs":{"certainty":{"$numberDouble":"0.22597971558570862"},"confusion":{"$numberDouble":"0.31543177366256714"},"neutral_statement":{"$numberDouble":"0.45858848094940186"}}}},"timestamp":{"$numberInt":"1762384375"}}

mock_collection.insert_one.return_value = MagicMock(
    json.dumps(dados_fic)
)


# 3. Mocks das dependências externas
# Para testes unitários limpos, o auth.verify_token deve ser mockado
def mock_verify_token_success():
    """Mock para simular autenticação bem-sucedida."""
    return "mocked_owner_token"

def mock_verify_token_failure():
    """Mock para simular falha na autenticação."""
    raise Exception("Token inválido simulado")

# ==========================================================
# FIXTURE PARA O CLIENTE DE TESTE
# ==========================================================

# Usamos patch.dict para simular os arquivos .keras existindo, senão a inicialização falha.
# Usamos patch para substituir a classe IntentClassifier e a função de conexão ao DB
@pytest.fixture(scope="session")
def client():
    # 1. Configurar Mocks ANTES de importar o app.main
    with patch.dict(os.environ, {"ENV": "test"}), \
         patch('db.engine.get_mongo_collection', return_value=mock_collection), \
         patch('app.app.get_mongo_collection', return_value=mock_collection), \
         patch('app.app.IntentClassifier', new=MockIntentClassifier), \
         patch('app.auth.verify_token', side_effect=mock_verify_token_success) as mock_auth_token:

        # 2. Importar o app SOMENTE após configurar todos os mocks globais
        from app.app import app
        
        # 3. Substituir a dependência conditional_auth para facilitar o teste
        # No DEV, não precisa de token. No PROD/TEST, precisa.
        def override_conditional_auth():
            """Mock da dependencia principal da rota /predict"""
            # No nosso teste, sempre vamos retornar o dono mockado
            return "mocked_owner_test_env"

        # Sobrescreve a dependência SÓ para o teste
        app.dependency_overrides[app.dependency_overrides.get('conditional_auth')] = override_conditional_auth
        
        with TestClient(app) as c:
            yield c
            
        # 4. Limpar o override no final
        app.dependency_overrides = {}


# ==========================================================
# TESTES DE INTEGRAÇÃO
# ==========================================================

# def test_root_endpoint(client: TestClient):
#     """Teste para verificar se a rota raiz funciona e retorna o modo TEST."""
#     response = client.get("/")
#     assert response.status_code == 200
#     assert response.json() == {"message": "Basic ML App is running in TEST mode"}


def test_predict_success(client: TestClient):
    """Teste de sucesso da rota /predict e se o DB é chamado."""
    text = "The report states with certainty that the project is on track."
    
    # ACT
    response = client.post(f"/predict?text={text}")
    
    # ASSERT
    assert response.status_code == 200
    data = response.json()
    
    # 1. Verifica se os dados do mock do modelo estão corretos
    assert data["predictions"]["confusion-v1"]["top_intent"] == "neutral_statement"
    
    # 2. Verifica se a dependência do owner foi injetada corretamente
    assert data["owner"] == "mocked_owner_test_env"
    
    # 3. Verifica se a coleção do DB foi chamada exatamente uma vez
    mock_collection.insert_one.assert_called_once()
    
    # 4. Verifica se a resposta contém o ID e removeu o _id binário
    assert "id" in data
    assert "_id" not in data


# def test_predict_different_intent(client: TestClient):
#     """Teste para um cenário de intenção diferente."""
#     text = "quem é você?"
    
#     response = client.post(f"/predict?text={text}")
    
#     assert response.status_code == 200
#     data = response.json()
    
#     assert data["predictions"]["confusion-v1"]["top_intent"] == "confusion"
    
#     # Limpa o histórico de chamadas do mock para o próximo teste
#     mock_collection.insert_one.reset_mock()


# # ==========================================================
# # TESTES DE AUTENTICAÇÃO (Sem o override_conditional_auth)
# # ==========================================================

# def test_predict_auth_failure():
#     """Testa se a autenticação falha corretamente no modo PROD/TEST."""
    
#     # 1. Configura o ambiente para forçar o erro de autenticação
#     with patch.dict(os.environ, {"ENV": "TEST"}), \
#          patch('db.engine.get_mongo_collection', return_value=mock_collection), \
#          patch('app.app.get_mongo_collection', return_value=mock_collection), \
#          patch('app.app.IntentClassifier', new=MockIntentClassifier), \
#          patch('os.listdir', return_value=['confusion-v1.keras']), \
#          patch('app.auth.verify_token', side_effect=mock_verify_token_failure): # << Mock de falha
        
#         # 2. Importa o app DENTRO do bloco patch para garantir que os mocks sejam aplicados
#         from app.app import app
        
#         # 3. Cria um novo cliente para esta execução de teste
#         client_auth_fail = TestClient(app)
        
#         # ACT: Tenta acessar a rota
#         response = client_auth_fail.post(f"/predict?text=teste")
        
#         # ASSERT: Espera o erro 401 do verify_token
#         assert response.status_code == 401
#         assert response.json()["detail"] == "Authentication failed"


# def test_predict_auth_dev_mode_skip():
#     """Testa se a autenticação é pulada no modo DEV."""
    
#     # 1. Configura o ambiente para DEV
#     with patch.dict(os.environ, {"ENV": "dev"}), \
#          patch('db.engine.get_mongo_collection', return_value=mock_collection), \
#          patch('app.app.get_mongo_collection', return_value=mock_collection), \
#          patch('app.app.IntentClassifier', new=MockIntentClassifier), \
#          patch('os.listdir', return_value=['confusion-v1.keras']), \
#          patch('app.auth.verify_token', side_effect=mock_verify_token_failure) as mock_auth_token:
        
#         # 2. Importa o app
#         from app.app import app
#         client_dev = TestClient(app)
        
#         # ACT
#         response = client_dev.post(f"/predict?text=teste")
        
#         # ASSERT
#         assert response.status_code == 200
#         data = response.json()
        
#         # 1. Verifica se pulou a autenticação
#         assert data["owner"] == "dev_user"
        
#         # 2. Verifica se o verify_token NUNCA foi chamado
#         mock_auth_token.assert_not_called()