import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# CONFIGURAÇÕES E PERSISTÊNCIA
# ==========================================
LINK_TESTE = "https://eng4redes.engeplus.com.br"
USUARIO = "gustavo.fernandes"
SENHA = "Almoxarifado4"
PRODUTO_NOME = "EQ19-1 - ROTEADOR - GPON / ONT ZTE F6600P"
ARQUIVO_CONTADOR = "contador_roteadores.txt"

def carregar_contador():
    if os.path.exists(ARQUIVO_CONTADOR):
        with open(ARQUIVO_CONTADOR, "r") as f:
            return int(f.read().strip())
    return 0

def salvar_contador(valor):
    with open(ARQUIVO_CONTADOR, "w") as f:
        f.write(str(valor))

def testar_login_e_clique():
    contador = carregar_contador()
    print(f"🚀 Iniciando automação... (Roteadores finalizados até agora: {contador})")
    
    opts = Options()
    opts.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    
    # --- NOVO: ABRIR EM TELA CHEIA ---
    driver.maximize_window() 
    # --------------------------------
    
    wait = WebDriverWait(driver, 15)

    try:
        print(f"🌐 Acessando: {LINK_TESTE}")
        driver.get(LINK_TESTE)

        # --- 1. LOGIN ---
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO)
        driver.find_element(By.ID, "password").send_keys(SENHA)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        
        # --- 2. MÓDULO ESTOQUE ---
        xpath_card = "//h3[contains(@class, 'module-title') and contains(., 'Estoque')]"
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_card))).click()

        # --- 3. EXPANDIR MENU (VIA JS) ---
        xpath_menu_pai = "//div[contains(@class, 'menu-group-title') and contains(., 'Estoque')]"
        menu_pai = wait.until(EC.presence_of_element_located((By.XPATH, xpath_menu_pai)))
        driver.execute_script("arguments[0].click();", menu_pai)
        time.sleep(2) 

        # --- 4. ESTOQUE GERAL ---
        xpath_estoque_geral = "//a[contains(@href, 'estoque.php') and contains(., 'Estoque Geral')]"
        submenu = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_estoque_geral)))
        driver.execute_script("arguments[0].click();", submenu)

        # --- 5. BOTÃO ENTRADA ---
        xpath_btn_entrada = "//a[contains(@class, 'btn-success') and .//span[contains(text(), 'Entrada')]]"
        wait.until(EC.element_to_be_clickable((By.XPATH, xpath_btn_entrada))).click()

        # --- 6. BUSCAR PRODUTO ---
        print(f"⌨️ Digitando produto: {PRODUTO_NOME}")
        campo_busca = wait.until(EC.visibility_of_element_located((By.ID, "busca_produto")))
        campo_busca.clear()
        campo_busca.send_keys(PRODUTO_NOME)
        time.sleep(2) 
        campo_busca.send_keys(Keys.ENTER)
        
        # --- SIMULAÇÃO DE FINALIZAÇÃO ---
        # (Quando você terminar o processo do roteador, incrementamos o contador)
        contador += 1
        salvar_contador(contador)
        print(f"✅ Sucesso! Novo total de roteadores: {contador}")

    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
    
    finally:
        print("💡 Script finalizado. Janela maximizada mantida.")

if __name__ == "__main__":
    testar_login_e_clique()