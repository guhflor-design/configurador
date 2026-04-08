import tkinter as tk
from tkinter import messagebox


def fazer_login():
    usuario = entry_usuario.get()
    senha = entry_senha.get()
    if usuario and senha:
        messagebox.showinfo("Login", f"Bem-vindo, {usuario}!")
    else:
        messagebox.showwarning("Login", "Preencha todos os campos!")


janela = tk.Tk()
janela.title("Tela de Login")
janela.geometry("300x200")
janela.resizable(False, False)

tk.Label(janela, text="Usuário:").pack(pady=(20, 5))
entry_usuario = tk.Entry(janela, width=30)
entry_usuario.pack()

tk.Label(janela, text="Senha:").pack(pady=(5, 5))
entry_senha = tk.Entry(janela, width=30, show="*")
entry_senha.pack()

tk.Button(janela, text="Entrar", command=fazer_login, width=15).pack(pady=15)

janela.mainloop()