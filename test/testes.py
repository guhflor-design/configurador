from selenium.webdriver.chrome.service import Service as ChromeService
import subprocess 
import os
import sys
import time
import requests
import threading
import pyautogui
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# FUNÇÃO PARA ARQUIVOS EMBUTIDOS (EXE)
# ==========================================
def resource_path(relative_path):
    """ Retorna o caminho real do arquivo, seja rodando script ou .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# CONFIGURAÇÕES DE CAMINHOS
# Tenta instalar a versão correta do driver para o Chrome do PC
try:
    # Limpa logs desnecessários e tenta a instalação padrão
    os.environ['WDM_LOG_LEVEL'] = '0'
    CHROME_PATH = ChromeDriverManager().install()
except Exception:
    # Se der erro de versão (ex: pedindo 143 em Chrome 145), força o reload
    os.environ['WDM_RELOAD_CHILDREN'] = "true"
    CHROME_PATH = ChromeDriverManager().install()
# O contador continua externo para salvar os dados permanentemente
DESKTOP_PATH = Path(os.environ["USERPROFILE"]) / "Desktop"
PASTA_PROG = DESKTOP_PATH / "programa_engeplus"
PASTA_PROG.mkdir(parents=True, exist_ok=True)
ARQUIVO_CONTADOR = PASTA_PROG / "contador_prod.txt"

# Arquivos que ficarão DENTRO do EXE (usando a função resource_path)
ARQUIVO_LOGO = resource_path("logo_engeplus.png")
ARQUIVO_BIN_3601S = resource_path("ZTE_H3601P Router Secundário.bin")
ARQUIVO_BIN_3601 = resource_path("ZTE_H3601P Router Primario Agent.bin")
ARQUIVO_BIN_6600 = resource_path("Versão 02.06.25.bin")
        
IP_ACESSO = "http://192.168.1.1"
IP_POS_CONFIG = "192.168.10.1" 

class PainelAutomacao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SISTEMA ENGEPLUS - F6600P / H3601P")
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
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{ts}] > {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def js_click(self, driver, element):
        """ Força o clique via JavaScript para ignorar bloqueios visuais """
        driver.execute_script("arguments[0].click();", element)

    def _montar_interface(self):
        self.grid_columnconfigure(0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.frame_sidebar = ctk.CTkFrame(self, fg_color="#112240", border_color="#00b4d8", border_width=2)
        self.frame_sidebar.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Carregamento da Logo
        try:
            img = Image.open(ARQUIVO_LOGO)
            img_logo = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 80))
            ctk.CTkLabel(self.frame_sidebar, image=img_logo, text="").pack(pady=(20, 10))
        except:
            ctk.CTkLabel(self.frame_sidebar, text="ENGEPLUS", font=("Segoe UI", 24, "bold"), text_color="#00b4d8").pack(pady=20)

        ctk.CTkLabel(self.frame_sidebar, text="MODELO SELECIONADO:", font=("Segoe UI", 13, "bold"), text_color="#00b4d8").pack(pady=(10, 5))
        self.combo_modelo = ctk.CTkComboBox(self.frame_sidebar, values=["ZTE F6600P", "ZTE H3601P","ZTE H3601P SECUNDÁRIO"], width=250, state="readonly")
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
        
        self.btn_parar = ctk.CTkButton(self.frame_main, text="PARAR TUDO", fg_color="#c62828", height=50, command=self.parar)
        self.btn_parar.pack(fill="x", pady=(0, 20))
        
        self.log_box = ctk.CTkTextbox(self.frame_main, fg_color="#050a14", text_color="#90e0ef", font=("Consolas", 12), state="disabled")
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
                                threading.Thread(target=self.fluxo_zte_3601, args=(ARQUIVO_BIN_3601,), daemon=True).start()
                            elif modelo == "ZTE H3601P SECUNDÁRIO":
                                threading.Thread(target=self.fluxo_zte_3601, args=(ARQUIVO_BIN_3601S,), daemon=True).start()
                            elif modelo == "ZTE F6600P":
                                threading.Thread(target=self.fluxo_f6600p, args=(ARQUIVO_BIN_6600,), daemon=True).start()
            except: pass
            time.sleep(1)

    def fluxo_f6600p(self):
        driver = None
        try:
            self.after(0, lambda: self.escrever_log("🔧 Iniciando F6600P..."))
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
            time.sleep(1)

            # Sair da config rápida (Ignora erro se não aparecer)
            try:
                btn_out = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "Outquicksetup")))
                self.js_click(driver, btn_out)
            except: pass
            
            # Navegação Serial (ID "Sn" Maiúsculo)
            wait.until(EC.element_to_be_clickable((By.ID, "internet"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "ponInfo"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "ponSn"))).click()
            
            sn = wait.until(EC.presence_of_element_located((By.ID, "Sn"))).get_attribute("value").strip().upper()
            self.after(0, lambda: self.escrever_log(f"🔢 Serial: {sn}"))

            # Upload com Clique JS no mrgAndDiag
            btn_mrg = wait.until(EC.presence_of_element_located((By.ID, "mrgAndDiag")))
            self.js_click(driver, btn_mrg)
            
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "ConfigMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()

            driver.execute_script("document.getElementById('DefCfgUpload').style.display = 'block';")
            driver.find_element(By.ID, "DefCfgUpload").send_keys(ARQUIVO_BIN_6600)
            
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
            self.after(0, lambda: self.escrever_log("⏳ Sucesso! Fechando em 10s..."))
            time.sleep(10)
            driver.quit()
            self.aguardar_ping_reboot()

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()

    def fluxo_zte_3601(self, caminho_bin):
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
            try:
                btn_close = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "Btn_Close")))
                self.js_click(driver, btn_close)
            except: pass

            btn_mrg = wait.until(EC.presence_of_element_located((By.ID, "mgrAndDiag")))
            self.js_click(driver, btn_mrg)
            
            sn = wait.until(EC.presence_of_element_located((By.ID, "SerialNumber"))).get_attribute("title").strip().upper()
            self.after(0, lambda: self.escrever_log(f"🔢 Serial: {sn}"))

            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
            btn_scroll = wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn")))
            webdriver.ActionChains(driver).click_and_hold(btn_scroll).perform()
            time.sleep(2)
            webdriver.ActionChains(driver).release().perform()
            
            wait.until(EC.element_to_be_clickable((By.ID, "defCfgMgr"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()
            
            driver.execute_script("document.getElementById('defConfigUpload').style.display = 'block';")
            driver.find_element(By.ID, "defConfigUpload").send_keys(caminho_bin)
            
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
            time.sleep(10) 
            driver.quit()
            self.aguardar_ping_reboot()

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro: {str(e).splitlines()[0]}"))
            if driver: driver.quit()
        finally:
            if self.lock_execucao.locked(): self.lock_execucao.release()

    def aguardar_ping_reboot(self):
        self.after(0, lambda: self.escrever_log(f"📡 Aguardando rede {IP_POS_CONFIG}..."))
        
        # Configuração para esconder a janela do CMD
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while True:
            # Executa o ping de forma invisível
            resultado = subprocess.run(
                ["ping", "-n", "1", "-w", "1000", IP_POS_CONFIG],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if resultado.returncode == 0:
                self.total_finalizados += 1
                self.after(0, lambda: self.val_contador.configure(text=str(self.total_finalizados)))
                ARQUIVO_CONTADOR.write_text(str(self.total_finalizados), encoding="utf-8")
                self.esperando_troca_de_cabo = True 
                self.aguardar_desconexao()
                break
            time.sleep(2)

    def aguardar_desconexao(self):
        self.after(0, lambda: self.escrever_log("🔌 TROQUE O EQUIPAMENTO."))
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        while True:
            resultado = subprocess.run(
                ["ping", "-n", "1", "-w", "500", IP_POS_CONFIG],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if resultado.returncode != 0: # Quando o ping falha, o cabo foi tirado
                break
            time.sleep(1)
            
        self.esperando_troca_de_cabo = False
        self.after(0, lambda: self.escrever_log("✅ Pronto para o próximo!"))

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()