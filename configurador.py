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
from selenium.common.exceptions import WebDriverException
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
        """Abre a interface do H3601P, faz upload e retorna o serial.

        O site usa frames internos e durante a navegação eles podem ser
        substituídos, o que faz o Selenium disparar um
        ``WebDriverException('target frame detached')``.  Em vez de abortar
        o fluxo, tentamos uma vez mais antes de falhar de vez.
        """

        attempts = 2  # número de tentativas em caso de frame desconectado
        sn_extraido = "N/A"

        while attempts:
            driver = None
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
                self.after(0, lambda: self.escrever_log("✅ Login realizado."))

                time.sleep(2)
                pyautogui.click(655, 378)
                time.sleep(1.5)
                wait.until(EC.element_to_be_clickable((By.ID, "Btn_Close"))).click()

                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()

                driver.switch_to.default_content()
                campo_sn = wait.until(EC.presence_of_element_located((By.ID, "SerialNumber")))
                sn_extraido = campo_sn.get_attribute("title").strip().upper()
                self.after(0, lambda s=sn_extraido: self.escrever_log(f"🔢 SN Capturado: {s}"))

                driver.switch_to.default_content()
                wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()

                # Navegação e upload
                driver.switch_to.default_content()
                btn = wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn")))
                actions = webdriver.ActionChains(driver)
                actions.click_and_hold(btn).perform()
                time.sleep(2)
                actions.release().perform()
                time.sleep(1)

                wait.until(EC.element_to_be_clickable((By.ID, "defCfgMgr"))).click()
                wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()
                elem = wait.until(EC.presence_of_element_located((By.ID, "defConfigUpload")))
                time.sleep(1)
                driver.execute_script("arguments[0].click();", elem)

                time.sleep(2)
                try:
                    driver.execute_script("""
                        var inputs = document.querySelectorAll("input[type='file']");
                        inputs.forEach(input => input.style.display = 'block');
                    """)
                    time.sleep(0.5)
                    file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
                    file_input.send_keys(ARQUIVO_BIN_3601)
                    time.sleep(1)
                    pyautogui.press('esc')
                    time.sleep(0.5)
                except Exception as e:
                    self.after(0, lambda: self.escrever_log(f"❌ Erro no upload: {str(e)}"))
                    raise

                self.after(0, lambda: self.escrever_log("⏳ Enviando configuração..."))
                wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
                wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
                self.after(0, lambda: self.escrever_log("✅ Configuração enviada. Aguardando..."))
                time.sleep(10)

                driver.quit()
                self.janela_de_cadastro(sn_extraido)
                return  # executado com sucesso, sai do método

            except WebDriverException as e:
                texto = str(e)
                if "target frame detached" in texto and attempts > 1:
                    self.after(0, lambda: self.escrever_log("⚠️ Frame desconectado. reiniciando tentativa..."))
                    if driver:
                        driver.quit()
                    attempts -= 1
                    continue  # tenta novamente
                # não é caso retriable ou esgotou tentativas
                self.after(0, lambda: self.escrever_log(f"❌ Erro Acesso: {texto.splitlines()[0]}"))
                if driver:
                    driver.quit()
                self.esperando_troca_de_cabo = False
                return
            except Exception as e:
                self.after(0, lambda: self.escrever_log(f"❌ Erro Acesso: {str(e).splitlines()[0]}"))
                if driver:
                    driver.quit()
                self.esperando_troca_de_cabo = False
                return
            finally:
                if self.lock_execucao.locked():
                    self.lock_execucao.release()

        # se esgotaram as tentativas sem sucesso
        self.esperando_troca_de_cabo = False

    # ================================================================
    # JANELA DE CADASTRO (UNIFICADA)
    # ================================================================
    def janela_de_cadastro(self, serial):
        modelo_atual = self.combo_modelo.get()
        nome_produto = NOMES_PRODUTOS.get(modelo_atual)

        self.after(0, lambda: self.escrever_log(f"🚀 MODO PRODUÇÃO: Iniciando Cadastro: {modelo_atual}..."))
        
        opts = Options()
        opts.add_experimental_option("detach", True) # Garante que a janela não feche
        opts.add_argument("--disable-blink-features=AutomationControlled")
        driver = None
        
        try:
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            driver.maximize_window()
            wait = WebDriverWait(driver, 20)
            
            # 1. ACESSO E LOGIN
            driver.get(LINK_SISTEMA)
            time.sleep(0.5) 
            
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USER_SISTEMA)
            time.sleep(0.5) 
            
            driver.find_element(By.ID, "password").send_keys(PASS_SISTEMA)
            time.sleep(0.5) 
            
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(0.5) 
            
            # 2. ENTRAR NO MÓDULO DE ESTOQUE
            wait.until(EC.element_to_be_clickable((By.XPATH, "//h3[contains(text(), 'Estoque')]"))).click()
            time.sleep(0.5) 

            # 3. NAVEGAÇÃO NO MENU LATERAL (POR ÍCONE)
            xpath_estoque = "//div[contains(@class, 'menu-group-title')][.//i[contains(@class, 'fa-boxes')]]"
            menu_estoque = wait.until(EC.presence_of_element_located((By.XPATH, xpath_estoque)))
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", menu_estoque)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", menu_estoque)
            time.sleep(0.5) 

            # --- SUBMENU: ESTOQUE GERAL ---
            sub_geral = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Estoque Geral')]")))
            driver.execute_script("arguments[0].click();", sub_geral)
            time.sleep(0.5) 
            
            # --- SUBMENU: ENTRADA ---
            sub_entrada = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Entrada')]")))
            driver.execute_script("arguments[0].click();", sub_entrada)
            time.sleep(0.5) 

            # 4. BUSCA DO PRODUTO
            campo_busca = wait.until(EC.visibility_of_element_located((By.ID, "busca_produto")))
            campo_busca.clear()
            campo_busca.send_keys(nome_produto)
            time.sleep(0.5) 
            
            campo_busca.send_keys(Keys.ENTER)
            time.sleep(0.5) 

            # 5. PREENCHIMENTO DO SERIAL
            campo_serial = wait.until(EC.presence_of_element_located((By.ID, "modal_mac_address")))
            campo_serial.clear()
            campo_serial.send_keys(serial)
            self.after(0, lambda: self.escrever_log(f"🔢 Serial {serial} preenchido!"))
            time.sleep(0.5) 
            
            # 6. ATUALIZAR CONTADOR (PERSISTENTE)
            self.total_finalizados += 1
            self.after(0, lambda: self.val_contador.configure(text=str(self.total_finalizados)))
            ARQUIVO_CONTADOR.write_text(str(self.total_finalizados), encoding="utf-8")
            self.after(0, lambda: self.escrever_log("🏁 Pronto para finalizar manualmente."))

        except Exception as e:
            self.after(0, lambda err=e: self.escrever_log(f"❌ Erro no Cadastro: {str(err).splitlines()[0]}"))
        finally:
            # Janela permanece aberta conforme solicitado
            self.esperando_troca_de_cabo = False
            if self.lock_execucao.locked():
                self.lock_execucao.release()

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()