import os
import time
import requests
import threading
import pyautogui
import customtkinter as ctk
from pathlib import Path
from PIL import Image # Necessário para processar a logo
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# CONFIGURAÇÕES DE CAMINHOS E IPS
# ==========================================
CHROME_PATH = ChromeDriverManager().install()
DESKTOP_PATH = Path(os.environ["USERPROFILE"]) / "Desktop"
PASTA_PROG = DESKTOP_PATH / "programa"
ARQUIVO_CONTADOR = PASTA_PROG / "contador_prod.txt"
ARQUIVO_LOGO = PASTA_PROG / "logo_engeplus.png" # Caminho da logo

PASTA_PROG.mkdir(parents=True, exist_ok=True)

IP_ACESSO = "http://192.168.1.1"
IP_POS_CONFIG = "192.168.10.1" 

# CAMINHOS DOS BINS
BASE_PATH_3601S = Path(r"C:\Users\gustavo.fernandes\OneDrive - SATC - Associação Beneficente da Indústria Carbonífera de Santa Catarina\fase 1\Área de Trabalho\routers\360\SECUNDARIO")
ARQUIVO_BIN_3601S = str(BASE_PATH_3601S / "ZTE_H3601P Router Secundário.bin")
BASE_PATH_3601 = Path(r"C:\Users\gustavo.fernandes\OneDrive - SATC - Associação Beneficente da Indústria Carbonífera de Santa Catarina\fase 1\Área de Trabalho\routers\360\PRIMARIO")
ARQUIVO_BIN_3601 = str(BASE_PATH_3601 / "ZTE_H3601P Router Primario Agent.bin")
BASE_PATH_6600 = Path(r"C:\Users\gustavo.fernandes\OneDrive - SATC - Associação Beneficente da Indústria Carbonífera de Santa Catarina\fase 1\Área de Trabalho\routers\6600")
ARQUIVO_BIN_6600 = str(BASE_PATH_6600 / "Versão 02.06.25.bin")

class PainelAutomacao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA DE ACESSO E REBOOT - ENGEPLUS")
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
    # 1. Habilita a escrita temporariamente
        self.log_box.configure(state="normal")
    # 2. Insere a mensagem com o timestamp
        self.log_box.insert("end", f"[{ts}] > {msg}\n")
    # 3. Faz o scroll automático para o final
        self.log_box.see("end")
    # 4. Bloqueia a edição novamente
        self.log_box.configure(state="disabled")

    def _montar_interface(self):
        self.grid_columnconfigure(0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.frame_sidebar = ctk.CTkFrame(self, fg_color="#112240", border_color="#00b4d8", border_width=2)
        self.frame_sidebar.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # --- SEÇÃO DA LOGO ---
        try:
            if ARQUIVO_LOGO.exists():
                img_logo = ctk.CTkImage(light_image=Image.open(ARQUIVO_LOGO),
                                        dark_image=Image.open(ARQUIVO_LOGO),
                                        size=(220, 80))
                self.label_logo = ctk.CTkLabel(self.frame_sidebar, image=img_logo, text="")
                self.label_logo.pack(pady=(20, 10))
            else:
                ctk.CTkLabel(self.frame_sidebar, text="ENGEPLUS", font=("Segoe UI", 24, "bold"), text_color="#00b4d8").pack(pady=20)
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")

        ctk.CTkLabel(self.frame_sidebar, text="MODELO SELECIONADO:", font=("Segoe UI", 13, "bold"), text_color="#00b4d8").pack(pady=(10, 5))
        
        self.combo_modelo = ctk.CTkComboBox(
            self.frame_sidebar, 
            values=["ZTE F6600P", "ZTE H3601P","ZTE H3601P SECUNDÁRIO"], 
            width=250,
            state="readonly"
        )
        self.combo_modelo.set("ZTE H3601P")
        self.combo_modelo.pack(pady=10)

        ctk.CTkLabel(self.frame_sidebar, text="PRODUÇÃO TOTAL", font=("Segoe UI", 16, "bold"), text_color="#00b4d8").pack(pady=(30, 0))
        self.val_contador = ctk.CTkLabel(self.frame_sidebar, text=str(self.total_finalizados), font=("Impact", 80), text_color="white")
        self.val_contador.pack(pady=10)
        
        ctk.CTkButton(self.frame_sidebar, text="ZERAR CONTADOR", fg_color="#334455", command=self.resetar_contador).pack(side="bottom", pady=20)

        self.frame_main = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_main.grid(row=1, column=1, padx=20, pady=10, sticky="nsew")
        
        self.btn_iniciar = ctk.CTkButton(self.frame_main, text="INICIAR MONITORAMENTO", fg_color="#27ae60", height=60, font=("Segoe UI", 18, "bold"), command=self.iniciar)
        self.btn_iniciar.pack(fill="x", pady=(0, 10))
        
        self.btn_parar = ctk.CTkButton(self.frame_main, text="PARAR TUDO", fg_color="#c62828", height=50, font=("Segoe UI", 16, "bold"), command=self.parar)
        self.btn_parar.pack(fill="x", pady=(0, 20))
        
        self.log_box = ctk.CTkTextbox(self.frame_main, fg_color="#050a14", text_color="#90e0ef", font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True)

    def iniciar(self):
        self.rodando = True
        self.btn_iniciar.configure(state="disabled")
        self.escrever_log(f"🔵 Monitorando {IP_ACESSO}...")
        threading.Thread(target=self.monitorar_rede, daemon=True).start()

    def parar(self):
        self.rodando = False
        self.btn_iniciar.configure(state="normal")
        self.escrever_log("🔴 Sistema parado.")

    def monitorar_rede(self):
        while self.rodando:
            try:
                if requests.get(IP_ACESSO, timeout=0.5).status_code == 200:
                    if not self.esperando_troca_de_cabo:
                        if self.lock_execucao.acquire(blocking=False):
                            modelo = self.combo_modelo.get()
                            if modelo == "ZTE H3601P":
                                threading.Thread(target=self.fluxo_zte_3601, daemon=True).start()
                            elif modelo == "ZTE H3601P SECUNDÁRIO":
                                threading.Thread(target=self.zte_3601_fluxo_secundario, daemon=True).start()
                            elif modelo == "ZTE F6600P":
                                threading.Thread(target=self.fluxo_f6600p, daemon=True).start()
                                
            except: pass
            time.sleep(1)

    def fluxo_zte_3601(self):
        driver = None
        try:
            self.after(0, lambda: self.escrever_log("🔓 Acessando H3601P..."))
            opts = Options()
            opts.add_argument("--window-size=1024,768") 
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            wait = WebDriverWait(driver, 20)

            driver.get(IP_ACESSO)
            wait.until(EC.presence_of_element_located((By.ID, "Frm_Username"))).send_keys("multipro")
            driver.find_element(By.ID, "Frm_Password").send_keys("multipro")
            driver.find_element(By.ID, "LoginId").click()
            
            time.sleep(2)
            pyautogui.click(668, 378) 
            time.sleep(1.5)
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Close"))).click()

            driver.switch_to.default_content()
            wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()
            campo_sn = wait.until(EC.presence_of_element_located((By.ID, "SerialNumber")))
            sn = campo_sn.get_attribute("title").strip().upper()
            self.after(0, lambda: self.escrever_log(f"🔢 Serial extraído: {sn}"))

            driver.switch_to.default_content()
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            btn_scroll = wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn")))
            webdriver.ActionChains(driver).click_and_hold(btn_scroll).perform()
            time.sleep(2)
            webdriver.ActionChains(driver).release().perform()
            
            wait.until(EC.element_to_be_clickable((By.ID, "defCfgMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()
            
            driver.execute_script("document.getElementById('defConfigUpload').style.display = 'block';")
            driver.find_element(By.ID, "defConfigUpload").send_keys(ARQUIVO_BIN_3601)
            
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
            self.after(0, lambda: self.escrever_log("⏳ Configuração enviada! Janela fechando em 10s..."))
            time.sleep(10) 
            driver.quit()

            self.janela_de_cadastro(sn)
            self.aguardar_ping_reboot()

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro no Fluxo: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
            self.esperando_troca_de_cabo = False
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()

    def aguardar_ping_reboot(self):
        self.after(0, lambda: self.escrever_log(f"📡 Aguardando reboot em {IP_POS_CONFIG}..."))
        while True:
            response = os.system(f"ping -n 1 -w 1000 {IP_POS_CONFIG} > nul")
            if response == 0:
                self.after(0, lambda: self.escrever_log("✨ Roteador Online (10.1)! TROQUE O EQUIPAMENTO."))
                self.total_finalizados += 1
                self.after(0, lambda: self.val_contador.configure(text=str(self.total_finalizados)))
                ARQUIVO_CONTADOR.write_text(str(self.total_finalizados), encoding="utf-8")
                self.esperando_troca_de_cabo = True 
                self.aguardar_desconexao()
                break
            time.sleep(2)

    def aguardar_desconexao(self):
        self.after(0, lambda: self.escrever_log("🔌 Aguardando desconexão do cabo..."))
        while True:
            response = os.system(f"ping -n 1 -w 500 {IP_POS_CONFIG} > nul")
            if response != 0: 
                self.after(0, lambda: self.escrever_log("✅ Cabo desconectado. Pronto para o próximo!"))
                self.esperando_troca_de_cabo = False
                break
            time.sleep(1)

    def janela_de_cadastro(self, serial):
        pass

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

    def js_click(self, driver, element):
        """ Força o clique via JavaScript, ignorando erros de 'elemento sobreposto' """
        driver.execute_script("arguments[0].click();", element)

    def fluxo_f6600p(self):
        driver = None
        try:
            self.after(0, lambda: self.escrever_log("🔧 Iniciando fluxo F6600P..."))
            opts = Options()
            opts.add_argument("--window-size=1024,768")
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            wait = WebDriverWait(driver, 20)

            driver.get(IP_ACESSO)
            wait.until(EC.presence_of_element_located((By.ID, "Frm_Username"))).send_keys("multipro")
            driver.find_element(By.ID, "Frm_Password").send_keys("multipro")
            driver.find_element(By.ID, "LoginId").click()

            time.sleep(2)
            pyautogui.click(668, 378) 
            time.sleep(2)

        # Sai da configuração rápida
            wait.until(EC.element_to_be_clickable((By.ID, "Outquicksetup"))).click()
            time.sleep(1.5)
        
        # Navegação com pausas para estabilidade
            self.after(0, lambda: self.escrever_log("Buscando Serial Number..."))
            wait.until(EC.element_to_be_clickable((By.ID, "internet"))).click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, "ponInfo"))).click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, "ponSn"))).click()
        
        # Captura do Serial
            campo_sn = wait.until(EC.presence_of_element_located((By.ID, "Sn")))
            sn = campo_sn.get_attribute("value").strip().upper()
            self.after(0, lambda: self.escrever_log(f"🔢 Serial extraído: {sn}"))
            time.sleep(1)

        # Navegação para Upload
            btn_mgr = wait.until(EC.element_to_be_clickable((By.ID, "mrgAndDiag"))).click()
            self.js_click(driver, btn_mgr)
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
        
        # Clique no scroll e ConfigMgr
            wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "ConfigMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUPloadBar"))).click()

        # Upload do arquivo - Verifique se o ID 'DefCfgUpload' está correto no F6600P
            self.after(0, lambda: self.escrever_log("Enviando configuração..."))
            driver.execute_script("document.getElementById('DefCfgUpload').style.display = 'block';")
        
        # Tenta encontrar o elemento de upload com segurança
            upload_element = driver.find_element(By.ID, "DefCfgUpload")
            if upload_element:
                upload_element.send_keys(ARQUIVO_BIN_6600)
                wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
                wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
                self.after(0, lambda: self.escrever_log("⏳ Configuração enviada! Janela fechando em 10s..."))
                time.sleep(10)
                driver.quit()
                self.janela_de_cadastro(sn)
                self.aguardar_ping_reboot()
            else:
                raise Exception("Campo de upload não encontrado (ID incorreto)")

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro no Fluxo: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
            self.esperando_troca_de_cabo = False
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()
        
    def zte_3601_fluxo_secundario(self):
        driver = None
        try:
            self.after(0, lambda: self.escrever_log("🔓 Acessando H3601P..."))
            opts = Options()
            opts.add_argument("--window-size=1024,768") 
            driver = webdriver.Chrome(service=Service(CHROME_PATH), options=opts)
            wait = WebDriverWait(driver, 20)

            driver.get(IP_ACESSO)
            wait.until(EC.presence_of_element_located((By.ID, "Frm_Username"))).send_keys("multipro")
            driver.find_element(By.ID, "Frm_Password").send_keys("multipro")
            driver.find_element(By.ID, "LoginId").click()
            
            time.sleep(2)
            pyautogui.click(668, 378) 
            time.sleep(1.5)
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Close"))).click()

            driver.switch_to.default_content()
            wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()
            campo_sn = wait.until(EC.presence_of_element_located((By.ID, "SerialNumber")))
            sn = campo_sn.get_attribute("title").strip().upper()
            self.after(0, lambda: self.escrever_log(f"🔢 Serial extraído: {sn}"))

            driver.switch_to.default_content()
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            btn_scroll = wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn")))
            webdriver.ActionChains(driver).click_and_hold(btn_scroll).perform()
            time.sleep(2)
            webdriver.ActionChains(driver).release().perform()
            
            wait.until(EC.element_to_be_clickable((By.ID, "defCfgMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()
            
            driver.execute_script("document.getElementById('defConfigUpload').style.display = 'block';")
            driver.find_element(By.ID, "defConfigUpload").send_keys(ARQUIVO_BIN_3601S)
            
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
            self.after(0, lambda: self.escrever_log("⏳ Configuração enviada! Janela fechando em 10s..."))
            time.sleep(10) 
            driver.quit()

            self.janela_de_cadastro(sn)
            self.aguardar_ping_reboot()

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro no Fluxo: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
            self.esperando_troca_de_cabo = False
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()
        

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()