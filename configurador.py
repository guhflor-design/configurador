import subprocess
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
ARQUIVO_LOGO = PASTA_PROG / "logo_engeplus.png" 
ARQUIVO_LOGO_LED = PASTA_PROG / "logo_led.png" 
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
        self.title("SISTEMA ENGEPLUS - AUTOMAÇÃO")
        self.geometry("1000x800")
        self.configure(fg_color="#0a192f")
        ctk.set_appearance_mode("dark")

        self.rodando = False
        self.testando_pings = False 
        self.lock_execucao = threading.Lock() 
        self.esperando_troca_de_cabo = False 
        self.total_finalizados = self.carregar_contador()
        # ===== LOGO LED =====
        self.logo_base = None
        self.logo_verde = None
        self.logo_vermelha = None

        if ARQUIVO_LOGO_LED.exists():
            self.logo_base = Image.open(ARQUIVO_LOGO_LED).convert("RGBA")

            # cria as versões UMA VEZ só
            self.logo_verde = self.colorir_logo((39, 174, 96))   # verde
            self.logo_vermelha = self.colorir_logo((198, 40, 40)) # vermelho

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

    def _montar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self, fg_color="#0a192f", segmented_button_selected_color="#00b4d8")
        self.tabview.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        
        self.tab_auto = self.tabview.add("AUTOMAÇÃO")
        self.tab_test = self.tabview.add("TESTE DE CONEXÃO")

        # --- ABA 1: AUTOMAÇÃO ---
        self.tab_auto.grid_columnconfigure(0, minsize=320)
        self.tab_auto.grid_columnconfigure(1, weight=1)
        self.tab_auto.grid_rowconfigure(0, weight=1)

        self.frame_sidebar = ctk.CTkFrame(self.tab_auto, fg_color="#112240", border_color="#00b4d8", border_width=2)
        self.frame_sidebar.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Logo
        try:
            if ARQUIVO_LOGO.exists():
                img = ctk.CTkImage(light_image=Image.open(ARQUIVO_LOGO), size=(200, 70))
                ctk.CTkLabel(self.frame_sidebar, image=img, text="").pack(pady=15)
        except: pass

        ctk.CTkLabel(self.frame_sidebar, text="MODELO SELECIONADO:", font=("Segoe UI", 13, "bold"), text_color="#00b4d8").pack(pady=(10, 5))
        self.combo_modelo = ctk.CTkComboBox(self.frame_sidebar, values=["ROTEADOR - GPON / ONT ZTE F6600P", "ROTEADOR SEM FIO / ZTE - H3601P", "SECUNDÁRIO - ROTEADOR SEM FIO / ZTE - H3601P"], width=260)
        self.combo_modelo.set("---SELECIONE O MODELO---")
        self.combo_modelo.pack(pady=10)

        ctk.CTkLabel(self.frame_sidebar, text="PRODUÇÃO TOTAL", font=("Segoe UI", 15, "bold"), text_color="#00b4d8").pack(pady=(20, 0))
        self.val_contador = ctk.CTkLabel(self.frame_sidebar, text=str(self.total_finalizados), font=("Impact", 85), text_color="white")
        self.val_contador.pack(pady=5)
        
        ctk.CTkButton(self.frame_sidebar, text="ZERAR CONTADOR", fg_color="#334455", height=35, command=self.resetar_contador).pack(side="bottom", pady=20)

        self.frame_main = ctk.CTkFrame(self.tab_auto, fg_color="transparent")
        self.frame_main.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.btn_iniciar = ctk.CTkButton(self.frame_main, text="INICIAR MONITORAMENTO", fg_color="#27ae60", height=60, font=("Segoe UI", 18, "bold"), command=self.iniciar)
        self.btn_iniciar.pack(fill="x", pady=(0, 10))
        
        self.btn_parar = ctk.CTkButton(self.frame_main, text="PARAR TUDO", fg_color="#c62828", height=45, font=("Segoe UI", 15, "bold"), command=self.parar)
        self.btn_parar.pack(fill="x", pady=(0, 15))
        
        self.log_box = ctk.CTkTextbox(self.frame_main, fg_color="#050a14", text_color="#90e0ef", font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True)

        # --- ABA 2: TESTE (DASHBOARD) ---
        self.ctrl_test = ctk.CTkFrame(self.tab_test, fg_color="#112240", height=80)
        self.ctrl_test.pack(fill="x", padx=15, pady=15)

        self.combo_ip_teste = ctk.CTkComboBox(self.ctrl_test, values=["192.168.1.1", "192.168.0.1", "192.168.3.1"], width=180, state="readonly" )
        self.combo_ip_teste.set("--- SELECIONE O IP ---")
        self.combo_ip_teste.pack(side="left", padx=20, pady=15)

        self.btn_test_ping = ctk.CTkButton(self.ctrl_test, text="LIGAR TESTES", fg_color="#1f538d", height=40, font=("Segoe UI", 14, "bold"), command=self.toggle_testes_ping)
        self.btn_test_ping.pack(side="right", padx=20)

        self.dash_frame = ctk.CTkFrame(self.tab_test, fg_color="transparent")
        self.dash_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.dash_frame.grid_columnconfigure((0,1), weight=1)

        self.card_left = self._criar_card_status(self.dash_frame, "ROTEADOR CONFIGURADO", "192.168.10.1", 0)
        self.card_right = self._criar_card_status(self.dash_frame, "ROTEADOR PADRÃO", "SELECIONADO", 1)

    def _criar_card_status(self, master, titulo, ip, col):
        frame = ctk.CTkFrame(master, fg_color="#112240", corner_radius=20, border_width=2, border_color="#1a3a5a")
        frame.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(frame, text=titulo, font=("Segoe UI", 15, "bold"), text_color="#00b4d8").pack(pady=(20, 5))
        ip_lbl = ctk.CTkLabel(frame, text=ip, font=("Consolas", 16), text_color="gray")
        ip_lbl.pack()
        
        led = ctk.CTkLabel(frame, text="")
        led.pack(pady=10)
        
        status_txt = ctk.CTkLabel(frame, text="AGUARDANDO...", font=("Segoe UI", 20, "bold"))
        status_txt.pack(pady=5)
        
        ms_txt = ctk.CTkLabel(frame, text="-- ms", font=("Segoe UI", 14), text_color="#00b4d8")
        ms_txt.pack(pady=(0, 20))
        
        return {"frame": frame, "led": led, "status": status_txt, "ms": ms_txt, "ip_lbl": ip_lbl}

    # ==========================================
    # LÓGICA DE PING (MODERNA)
    # ==========================================
    def toggle_testes_ping(self):
        if not self.testando_pings:
            self.testando_pings = True
            self.btn_test_ping.configure(text="DESLIGAR", fg_color="#c62828")
            ip_din = self.combo_ip_teste.get()
            self.card_right["ip_lbl"].configure(text=ip_din)
            threading.Thread(target=self.loop_ping_led, args=("192.168.10.1", self.card_left), daemon=True).start()
            threading.Thread(target=self.loop_ping_led, args=(ip_din, self.card_right), daemon=True).start()
        else:
            self.testando_pings = False
            self.btn_test_ping.configure(text="LIGAR TESTES", fg_color="#23cf40")

    def loop_ping_led(self, ip, widgets):
        falhas_consecutivas = 0
        limite_falhas = 3  # Só fica vermelho após 3 erros seguidos

        while self.testando_pings:
            try:
                # -n 1 (um pacote), -w 1000 (espera até 1 segundo)
                out = subprocess.check_output(
                    f"ping -n 1 -w 1000 {ip}", 
                    creationflags=0x08000000
                ).decode('utf-8', errors='ignore')

                if "tempo=" in out or "time=" in out:
                    # SUCESSO: Reseta o contador de falhas e atualiza para verde
                    falhas_consecutivas = 0
                    part = out.split("tempo=")[1] if "tempo=" in out else out.split("time=")[1]
                    ms = part.split("ms")[0].strip()
                    self.after(0, lambda: self.atualizar_led(widgets, True, ms))
                else:
                    # FALHA MOMENTÂNEA
                    falhas_consecutivas += 1
                    if falhas_consecutivas >= limite_falhas:
                        self.after(0, lambda: self.atualizar_led(widgets, False))
            except:
                # ERRO DE EXCEÇÃO
                falhas_consecutivas += 1
                if falhas_consecutivas >= limite_falhas:
                    self.after(0, lambda: self.atualizar_led(widgets, False))
            
            time.sleep(0.5) # Intervalo curto para resposta rápida, mas sem sobrecarregar

    def atualizar_led(self, widgets, online, ms=""):
        if online:
            if self.logo_verde:
                widgets["led"].configure(image=self.logo_verde, text="")
                widgets["led"].image = self.logo_verde

            widgets["status"].configure(text="CONECTADO", text_color="#27ae60")
            widgets["ms"].configure(text=f"Latência: {ms}ms")
            widgets["frame"].configure(border_color="#27ae60")

        else:
            if self.logo_vermelha:
                widgets["led"].configure(image=self.logo_vermelha, text="")
                widgets["led"].image = self.logo_vermelha

            widgets["status"].configure(text="FALHA", text_color="#c62828")
            widgets["ms"].configure(text="Sem resposta")
            widgets["frame"].configure(border_color="#c62828")

    # ==========================================
    # LÓGICA DE AUTOMAÇÃO (MANTIDA)
    # ==========================================
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
                # Tenta pingar o roteador
                if requests.get(IP_ACESSO, timeout=0.5).status_code == 200:
                    if not self.esperando_troca_de_cabo:
                        # Tenta pegar o Lock para não abrir dois Chromes
                        if self.lock_execucao.acquire(blocking=False):
                            modelo = self.combo_modelo.get()
                            
                            # --- LÓGICA OTIMIZADA PARA ZTE H3601P ---
                            if "ROTEADOR SEM FIO / ZTE - H3601P" in modelo:
                                # Se a palavra SECUNDÁRIO estiver no nome, usa o bin de secundário
                                arquivo = ARQUIVO_BIN_3601S if "SECUNDÁRIO" in modelo else ARQUIVO_BIN_3601
                                
                                self.escrever_log(f"⚡ Iniciando H3601P ({'Secundário' if 'SECUNDÁRIO' in modelo else 'Primário'})")
                                
                                # Chama a função única passando o arquivo correto como argumento (args)
                                threading.Thread(
                                    target=self.fluxo_zte_3601_universal, 
                                    args=(arquivo,), 
                                    daemon=True
                                ).start()

                            # --- LÓGICA PARA F6600P ---
                            elif "ROTEADOR - GPON / ONT ZTE F6600P" in modelo:
                                self.escrever_log("⚡ Iniciando Fluxo F6600P...")
                                threading.Thread(target=self.fluxo_f6600p, daemon=True).start()
                                
            except Exception:
                # Silencia erros de conexão (comum enquanto o roteador reinicia)
                pass
            
            time.sleep(1)
            
    def colorir_logo(self, cor):
        if self.logo_base is None:
           return None

        img = self.logo_base.copy()
        r, g, b = cor

        pixels = img.load()
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                pr, pg, pb, pa = pixels[x, y]
                if pa > 0:
                    pixels[x, y] = (r, g, b, pa)

        return ctk.CTkImage(light_image=img, size=(60, 60))
    
    def js_click(self, driver, element):
        """ Força o clique via JavaScript, ignorando erros de 'elemento sobreposto' """
        driver.execute_script("arguments[0].click();", element)

    
    # --- FLUXOS SELENIUM (IGUAIS AOS SEUS ORIGINAIS) ---
    def fluxo_zte_3601_universal(self, caminho_bin):
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
            # NA HORA DO UPLOAD, usamos a variável 'caminho_bin' que veio por parâmetro:
            driver.execute_script("document.getElementById('defConfigUpload').style.display = 'block';")
            driver.find_element(By.ID, "defConfigUpload").send_keys(caminho_bin)
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.ID, "Btn_Upload"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "confirmOK"))).click()
            
            self.after(0, lambda: self.escrever_log("⏳ Configuração enviada! Janela fechando em 10s..."))
            time.sleep(10) 
            driver.quit()

            self.janela_de_cadastro(sn)
            self.aguardar_ping_reboot()
            # ... (Resto do código de confirmação e reboot) ...

        except Exception as e:
            self.after(0, lambda: self.escrever_log(f"❌ Erro: {str(e).splitlines()[0]}"))
        finally:
            if driver: driver.quit()
            if self.lock_execucao.locked(): self.lock_execucao.release()

    def fluxo_f6600p(self):
        # ... Insira aqui o conteúdo do seu fluxo_f6600p original ...
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
            pyautogui.click(668, 378) 
            time.sleep(2)

        # Tenta sair da configuração rápida, mas continua se o botão não estiver lá
            try:
                self.after(0, lambda: self.escrever_log("Tentando fechar configuração rápida..."))
                # Diminuímos o tempo de espera (timeout) para 3 segundos para não travar o código se não existir
                btn_out = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, "Outquicksetup")))
                self.js_click(driver, btn_out)
                time.sleep(1.5)
            except Exception:
                self.after(0, lambda: self.escrever_log("Botão de saída não encontrado ou já fechado. Seguindo..."))
        
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
            wait.until(EC.element_to_be_clickable((By.ID, "mgrAndDiag"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "devMgr"))).click()
        
        # Clique no scroll e ConfigMgr
            wait.until(EC.element_to_be_clickable((By.ID, "scrollRightBtn"))).click()
            wait.until(EC.element_to_be_clickable((By.ID, "ConfigMgr"))).click()
            time.sleep(0.5)
            wait.until(EC.element_to_be_clickable((By.ID, "DefConfUploadBar"))).click()

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
                time.sleep(20)
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

    def resetar_contador(self):
        self.total_finalizados = 0
        self.val_contador.configure(text="0")
        ARQUIVO_CONTADOR.write_text("0", encoding="utf-8")

if __name__ == "__main__":
    app = PainelAutomacao()
    app.mainloop()