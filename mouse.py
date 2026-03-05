import pyautogui
import time

print("Pressione Ctrl-C para parar.")

try:
    while True:
        # Obtém a posição atual do mouse
        x, y = pyautogui.position()
        
        # Formata a string para exibir as coordenadas
        posicao = f"Posição do mouse: X={x:4d} Y={y:4d}"
        
        # Imprime na mesma linha usando \r (retorno de carro)
        print(posicao, end="\r")
        
        # Pequena pausa para não sobrecarregar o processador
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nPrograma finalizado.")