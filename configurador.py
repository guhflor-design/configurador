import os
import time
import requests
import threading
import pyautogui
import customtkinter as ctk
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# CONFIGURAÇÕES DE CAMINHOS LOCAIS
# ==========================================
CHROME_PATH = ChromeDriverManager().install()
DESKTOP_PATH = Path(os.environ["USERPROFILE"]) / "Desktop"
PASTA_PROG = DESKTOP_PATH / "programa"
ARQUIVO_CONTADOR = PASTA_PROG / "contador_prod.txt"

# CAMINHOS DOS BINS (BUSCANDO DA ÁREA DE TRABALHO REAL)
# --- Caminho exato do F6600P ---
BASE_PATH_6600 = Path(r"C:\Users\gustavo.fernandes\OneDrive - SATC - Associação Beneficente da Indústria Carbonífera de Santa Catarina\fase 1\Área de Trabalho\routers\6600")
ARQUIVO_BIN_6600 = str(BASE_PATH_6600 / "Versão 02.06.25.bin")

# --- Caminho exato do H3601P ---
BASE_PATH_3601 = Path(r"C:\Users\gustavo.fernandes\OneDrive - SATC - Associação Beneficente da Indústria Carbonífera de Santa Catarina\fase 1\Área de Trabalho\routers\360")
ARQUIVO_BIN_3601 = str(BASE_PATH_3601 / "ZTE_H3601P Router Primario Agent.bin")

# CONFIG JANELA DE CADASTRO
LINK_SISTEMA = "https://eng4redes.engeplus.com.br"
USER_SISTEMA = "gustavo.fernandes"
PASS_SISTEMA = "Almoxarifado4"

# DICIONÁRIO DE NOMES POR MODELO
NOMES_PRODUTOS = {
    "ZTE F6600P": "EQ19-1 - ROTEADOR - GPON / ONT ZTE F6600P",
    "ZTE H3601P": "EQ11-3 - ROTEADOR SEM FIO / ZTE - H3601P" 
}

class PainelAutomacao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA DE AUTOMAÇÃO - ENGEPLUS")
        self.geometry("1000x750")
        self.configure(fg_color="#0a192f")
        ctk.set_appearance_mode("dark")

        self.rodando = False
        self.lock_execucao = threading.Lock() 
        self.esperando_troca_de_cabo = False 
        self.total_finalizados = self.carregar_contador()

        self._montar_interface()

    def carregar_contador(self):
        try:
            if ARQUIVO_CONTADOR.exists():
                return int(ARQUIVO_CONTADOR.read_text(encoding="utf-8").strip())
        except: pass
        return 0

    def escrever_log(self, msg):
        ts = time.strftime('%H:%M:%S')
        self.log_box.insert("end", f"[{ts}] > {msg}\n")
        self.log_box.see("end")

    def _montar_interface(self):
        self.grid_columnconfigure(0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.frame_sidebar = ctk.CTkFrame(self, fg_color="#112240", border_color="#00b4d8", border_width=2)
        self.frame_sidebar.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        ctk.CTkLabel(self.frame_sidebar, text="MODELO SELECIONADO:", font=("Segoe UI", 13, "bold"), text_color="#00b4d8").pack(pady=(20, 5))
        self.combo_modelo = ctk.CTkComboBox(self.frame_sidebar, values=["ZTE F6600P", "ZTE H3601P"], width=250)
        self.combo_modelo.pack(pady=10)

        ctk.CTkLabel(self.frame_sidebar, text="PRODUÇÃO TOTAL", font=("Segoe UI", 16, "bold"), text_color="#00b4d8").pack(pady=(30, 0))
        self.val_contador = ctk.CTkLabel(self.frame_sidebar, text=str(self.total_finalizados), font=("Impact", 80), text_color="white")
        self.val_contador.pack(pady=10)
        
        ctk.CTkButton(self.frame_sidebar, text="ZERAR CONTADOR", fg_color="#334455", command=self.resetar_contador).pack(side="bottom", pady=20)

        self.frame_main = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_main.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        
        self.btn_iniciar = ctk.CTkButton(self.frame_main, text="INICIAR SISTEMA", fg_color="#27ae60", height=60, font=("Segoe UI", 18, "bold"), command=self.iniciar)
        self.btn_iniciar.pack(fill="x", pady=(0, 10))
        
        self.btn_parar = ctk.CTkButton(self.frame_main, text="PARAR TUDO", fg_color="#c62828", height=50, font=("Segoe UI", 16, "bold"), command=self.parar)
        self.btn_parar.pack(fill="x", pady=(0, 20))
        
        self.log_box = ctk.CTkTextbox(self.frame_main, fg_color="#050a14", text_color="#90e0ef", font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True)

    def iniciar(self):
        self.rodando = True
        self.btn_iniciar.configure(state="disabled")
        self.escrever_log(f"🔵 Monitoramento ativo. Modelo: {self.combo_modelo.get()}")
        threading.Thread(target=self.monitorar_rede, daemon=True).start()

    def parar(self):
        self.rodando = False
        self.btn_iniciar.configure(state="normal")
        self.escrever_log("🔴 Sistema parado.")

    def monitorar_rede(self):
        while self.rodando:
            try:
                if requests.get("http://192.168.1.1", timeout=0.5).status_code == 200:
                    if not self.esperando_troca_de_cabo:
                        if self.lock_execucao.acquire(blocking=False):
                            modelo = self.combo_modelo.get()
                            if modelo == "ZTE F6600P":
                                threading.Thread(target=self.fluxo_zte_6600, daemon=True).start()
                            elif modelo == "ZTE H3601P":
                                threading.Thread(target=self.fluxo_zte_3601, daemon=True).start()
                            self.esperando_troca_de_cabo = True
            except: pass
            time.sleep(1)

    # ================================================================
    # FLUXOS DE ACESSO
    # ================================================================
    
    def fluxo_zte_6600(self):
        # ... (Implementar os caminhos corretos do 6600 aqui depois) ...
        self.after(0, lambda: self.escrever_log("🤖 Fluxo 6600P não implementado."))
        self.esperando_troca_de_cabo = False
        if self.lock_execucao.locked(): self.lock_execucao.release()

    def fluxo_zte_3601(self):
        driver = None
        sn_extraido = "N/A"
        try:
            self.after(0, lambda: self.escrever_log("🔓 Abrindo JANELA DE ACESSO (H3601P)..."))
            opts = Options()
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            wait = WebDriverWait(driver, 20) 

            driver.get("http://192.168.1.1")
            
            # Login
            wait.until(EC.presence_of_element_located((By.ID, "Frm_Username"))).send_keys("multipro")
            driver.find_element(By.ID, "Frm_Password").send_keys("multipro")
            driver.find_element(By.ID, "LoginId").click()
            
            # --- POPUP: Espera 2s e Clica Instantaneamente ---
            self.after(0, lambda: self.escrever_log("⏳ Aguardando carregamento do pop-up..."))
            time.sleep(2) 
            
            self.after(0, lambda: self.escrever_log("🖱️ Clicando instantaneamente para fechar pop-up..."))
            # duration=0 faz o mouse ir instantaneamente para o local
            pyautogui.click(655, 378)
            self.after(0, lambda: self.escrever_log("✅ Pop-up inicial fechado (clique instantâneo)."))

            # --- Sai da config rápida ---
            self.after(0, lambda: self.escrever_log("⏳ Clicando em sair da configuração rápida..."))
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Close"))).click()
            self.after(0, lambda: self.escrever_log("✅ Saiu da configuração rápida."))
            
            # --- Navegação Robusta ---
            
            # 1. Clicar em "Gerenciamento & Diagnóstico"
            self.after(0, lambda: self.escrever_log("⏳ Aguardando menu Gerenciamento..."))
            wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()
            self.after(0, lambda: self.escrever_log("✅ Menu Gerenciamento aberto."))
            
            # 2. Captura do Serial
            self.after(0, lambda: self.escrever_log("⏳ Capturando Serial Number..."))
            campo_sn = wait.until(EC.presence_of_element_located((By.ID, "SerialNumber")))
            sn_extraido = campo_sn.get_attribute("title").strip().upper()
            self.after(0, lambda s=sn_extraido: self.escrever_log(f"🔢 SN Capturado: {s}"))
            
            # 3. Clicar em "Gerenciamento de sistema"
            self.after(0, lambda: self.escrever_log("⏳ Expandindo submenu Sistema..."))
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            
            # --- NOVO: Fazer o scroll para a direita para ver o menu ---
            self.after(0, lambda: self.escrever_log("⏳ Fazendo scroll para a direita..."))
            
            # Pega a localização do botão na tela para garantir o clique
            btn_scroll = wait.until(EC.presence_of_element_located((By.ID, "scrollRightBtn")))
            location = btn_scroll.location_once_scrolled_into_view
            
            # Clica usando PyAutoGUI baseado na posição do Selenium
            pyautogui.click(location['x'] + 10, location['y'] + 130) # Ajuste de offset para o clique
            
            time.sleep(1) # Tempo para a rolagem acontecer

            # 4. Clicar no sub-item "Configuração de gerência padrão"
            self.after(0, lambda: self.escrever_log("⏳ Clicando em Configuração de gerência padrão..."))
            # ID do sub-item que agora deve estar visível
            wait.until(EC.element_to_be_clickable((By.ID, "ConfigUpload"))).click()
            self.after(0, lambda: self.escrever_log("✅ Submenu aberto."))

            # --- FLUXO DE UPLOAD BIN DO H3601P ---
            self.after(0, lambda: self.escrever_log("⏳ Iniciando Upload do BIN..."))
            
            # Ação do gerenciador de arquivos do Windows (pyautogui)
            time.sleep(2) 
            pyautogui.write(ARQUIVO_BIN_3601)
            pyautogui.press('enter')
            self.after(0, lambda: self.escrever_log("✅ Arquivo selecionado."))
            
            # 5. Clicar no botão 'Restaurar Configuração'
            self.after(0, lambda: self.escrever_log("⏳ Clicando em Restaurar Configuração..."))
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            self.after(0, lambda: self.escrever_log("✅ Botão Restaurar clicado."))
            
            # 6. Clicar no botão 'OK' do pop-up de confirmação
            self.after(0, lambda: self.escrever_log("⏳ Confirmando pop-up..."))
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            self.after(0, lambda: self.escrever_log("✅ Confirmação enviada."))
            
            # --- PAUSA DE 10 SEGUNDOS APÓS CONFIRMAÇÃO ---
            self.after(0, lambda: self.escrever_log("⏳ Aguardando 10 segundos para iniciar Cadastro..."))
            time.sleep(10) 
            
            driver.quit()
            
            # Chamar Janela de Cadastro com SN capturado
            self.janela_de_cadastro(sn_extraido)

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro Acesso: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
            self.esperando_troca_de_cabo = False 
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()

    # ================================================================
    # JANELA DE CADASTRO (UNIFICADA)
    # ================================================================
    def janela_de_cadastro(self, serial):
        modelo_atual = self.combo_modelo.get()
        nome_produto = NOMES_PRODUTOS.get(modelo_atual)

        self.after(0, lambda: self.escrever_log(f"📋 Abrindo JANELA DE CADASTRO para {modelo_atual}..."))
        opts = Options()
        driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
        driver.maximize_window()
        wait = WebDriverWait(driver, 20)
        
        try:
            driver.get(LINK_SISTEMA)
            # Login
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USER_SISTEMA)
            driver.find_element(By.ID, "password").send_keys(PASS_SISTEMA)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Navegação
            wait.until(EC.element_to_be_clickable((By.XPATH, "//h3[contains(., 'Estoque')]"))).click()
            menu_pai = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Estoque')]")))
            driver.execute_script("arguments[0].click();", menu_pai)
            
            submenu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Estoque Geral')]")))
            driver.execute_script("arguments[0].click();", submenu)
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Estoque Geral')]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Entrada')]"))).click()
            
            # Busca do Produto e preenchimento do SN
            campo_busca = wait.until(EC.visibility_of_element_located((By.ID, "busca_produto")))
            campo_busca.send_keys(nome_produto)
            campo_busca.send_keys(Keys.ENTER)
            time.sleep(2)

            campo_serial = wait.until(EC.presence_of_element_located((By.ID, "modal_mac_address")))
            campo_serial.clear()
            campo_serial.send_keys(serial)
            self.after(0, lambda: self.escrever_log(f"✅ {modelo_atual} cadastrado com sucesso!"))

            # Salva contador
            self.total_finalizados += 1
            self.after(0, lambda: self.val_contador.configure(text=str(self.total_finalizados)))
            ARQUIVO_CONTADOR.write_text(str(self.total_finalizados), encoding="utf-8")
            
        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro Cadastro: {str(e)}"))
        finally:
            driver.quit()
            self.esperando_troca_de_cabo = False

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()