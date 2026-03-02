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

# CAMINHO DO BIN (BUSCANDO DA ÁREA DE TRABALHO REAL)
ARQUIVO_BIN = str(DESKTOP_PATH / "routers" / "6600" / "Versão 02.06.25.bin")

# CONFIG JANELA DE CADASTRO
LINK_SISTEMA = "https://eng4redes.engeplus.com.br"
USER_SISTEMA = "gustavo.fernandes"
PASS_SISTEMA = "Almoxarifado4"
PRODUTO_NOME = "EQ19-1 - ROTEADOR - GPON / ONT ZTE F6600P"

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

        # Lateral
        self.frame_sidebar = ctk.CTkFrame(self, fg_color="#112240", border_color="#00b4d8", border_width=2)
        self.frame_sidebar.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        ctk.CTkLabel(self.frame_sidebar, text="MODELO SELECIONADO:", font=("Segoe UI", 13, "bold"), text_color="#00b4d8").pack(pady=(20, 5))
        self.combo_modelo = ctk.CTkComboBox(self.frame_sidebar, values=["ZTE F6600P"], width=250)
        self.combo_modelo.pack(pady=10)

        ctk.CTkLabel(self.frame_sidebar, text="PRODUÇÃO TOTAL", font=("Segoe UI", 16, "bold"), text_color="#00b4d8").pack(pady=(30, 0))
        self.val_contador = ctk.CTkLabel(self.frame_sidebar, text=str(self.total_finalizados), font=("Impact", 80), text_color="white")
        self.val_contador.pack(pady=10)
        
        ctk.CTkButton(self.frame_sidebar, text="ZERAR CONTADOR", fg_color="#334455", command=self.resetar_contador).pack(side="bottom", pady=20)

        # Principal
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
        self.escrever_log("🔵 Monitoramento iniciado...")
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
                            threading.Thread(target=self.fluxo_zte_6600, daemon=True).start()
                            self.esperando_troca_de_cabo = True
            except: pass
            time.sleep(1)

    # ================================================================
    # JANELA DE ACESSO (ROUTER ZTE 6600)
    # ================================================================
    def fluxo_zte_6600(self):
        driver = None
        sn_extraido = "N/A"
        try:
            self.after(0, lambda: self.escrever_log("🔓 Abrindo JANELA DE ACESSO..."))
            opts = Options()
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            wait = WebDriverWait(driver, 15)

            driver.get("http://192.168.1.1")
            wait.until(EC.presence_of_element_located((By.ID, "Frm_Username"))).send_keys("multipro")
            driver.find_element(By.ID, "Frm_Password").send_keys("multipro")
            driver.find_element(By.ID, "LoginId").click()
            
            time.sleep(3)
            try: pyautogui.click(x=789, y=368) # Fecha popup
            except: pass
            
            driver.execute_script("document.getElementById('Outquicksetup').click();")
            time.sleep(1)

            # Captura do Serial
            wait.until(EC.element_to_be_clickable((By.ID, "internet"))).click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, "ponInfo"))).click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, "ponSn"))).click()
            campo_sn = wait.until(EC.presence_of_element_located((By.ID, "Sn")))
            sn_extraido = campo_sn.get_attribute("value").strip().upper()
            self.after(0, lambda s=sn_extraido: self.escrever_log(f"🔢 SN Capturado: {s}"))

            # Upload do BIN
            wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            driver.execute_script("document.getElementById('ConfigMgr').click();")
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()
            driver.find_element(By.ID, "DefCfgUpload").send_keys(ARQUIVO_BIN)
            driver.find_element(By.ID, "Btn_Upload").click()
            time.sleep(1)
            pyautogui.press('enter')
            
            self.after(0, lambda: self.escrever_log("📤 BIN enviado. Aguardando 10s para JANELA DE CADASTRO..."))
            time.sleep(10)
            driver.quit()

            # Chamar Janela de Cadastro
            self.janela_de_cadastro(sn_extraido)

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro Acesso: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
            self.esperando_troca_de_cabo = False 
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()

    # ================================================================
    # JANELA DE CADASTRO (SISTEMA ENG4REDES)
    # ================================================================
    def janela_de_cadastro(self, serial):
        self.after(0, lambda: self.escrever_log("📋 Abrindo JANELA DE CADASTRO..."))
        opts = Options()
        driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
        driver.maximize_window()
        wait = WebDriverWait(driver, 20)
        
        try:
            driver.get(LINK_SISTEMA)
            # Login sistema
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USER_SISTEMA)
            driver.find_element(By.ID, "password").send_keys(PASS_SISTEMA)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
            # Navegação Estoque
            wait.until(EC.element_to_be_clickable((By.XPATH, "//h3[contains(., 'Estoque')]"))).click()
            menu_pai = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Estoque')]")))
            driver.execute_script("arguments[0].click();", menu_pai)
            
            submenu = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Estoque Geral')]")))
            driver.execute_script("arguments[0].click();", submenu)
            
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Entrada')]"))).click()
            
            # Busca e Preenchimento de SN
            campo_busca = wait.until(EC.visibility_of_element_located((By.ID, "busca_produto")))
            campo_busca.send_keys(PRODUTO_NOME)
            campo_busca.send_keys(Keys.ENTER)
            time.sleep(2)

            campo_serial = wait.until(EC.presence_of_element_located((By.ID, "modal_mac_address")))
            campo_serial.clear()
            campo_serial.send_keys(serial)
            self.after(0, lambda: self.escrever_log(f"✅ Serial {serial} inserido no sistemaa!"))

            # Salva contador
            self.total_finalizados += 1
            self.after(0, lambda: self.val_contador.configure(text=str(self.total_finalizados)))
            ARQUIVO_CONTADOR.write_text(str(self.total_finalizados), encoding="utf-8")
            
            self.verificar_ip_final()

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro Cadastro: {str(e)}"))
        finally:
            driver.quit()

    def verificar_ip_final(self):
        self.after(0, lambda: self.escrever_log("🔍 Aguardando IP 10.1 para finalizar..."))
        while self.rodando:
            try:
                if requests.get("http://192.168.10.1", timeout=0.8).status_code == 200:
                    self.after(0, lambda: self.escrever_log("🏁 FINALIZADO! Pode trocar o cabo."))
                    self.esperando_troca_de_cabo = False 
                    return
            except: pass
            time.sleep(2)

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()