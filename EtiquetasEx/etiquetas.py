from PIL import Image, ImageTk, ImageDraw, ImageFont
import tkinter as tk
from tkinter import messagebox
import barcode
from barcode.writer import ImageWriter
import sqlite3

# Conexão com o banco de dados SQLite (será criado automaticamente se não existir)
conn = sqlite3.connect('barcodes.db')
cursor = conn.cursor()

# Criação da tabela para armazenar os códigos de barras, se ainda não existir
cursor.execute('''
    CREATE TABLE IF NOT EXISTS barcodes (
        id INTEGER PRIMARY KEY,
        color TEXT NOT NULL,
        barcode TEXT NOT NULL
    )
''')

# Dicionário para armazenar os códigos de barras gerados
generated_barcodes = {}

def generate_barcode():
    color = color_entry.get()
    if not color:
        messagebox.showwarning("Input Error", "Por favor, insira uma cor.")
        return
    
    # Verificar se a cor já tem um código de barras gerado
    cursor.execute('SELECT barcode FROM barcodes WHERE color=?', (color,))
    result = cursor.fetchone()
    
    if result:
        # Se já existe, usar o código de barras existente
        ean_code = result[0]
    else:
        # Gerar um novo código de barras
        base_code = '789671423114'  # Base do código
        ean_code = base_code[:-len(str(len(generated_barcodes) + 1))] + str(len(generated_barcodes) + 1)
        generated_barcodes[color] = ean_code
        
        # Inserir o novo código de barras no banco de dados
        cursor.execute('INSERT INTO barcodes (color, barcode) VALUES (?, ?)', (color, ean_code))
        conn.commit()
    
    # Gerar o código de barras
    ean = barcode.get('ean13', ean_code, writer=ImageWriter())
    filename = f"barcode_{color}"
    ean.save(filename)
    
    # Abrir a imagem gerada e redimensionar para 400x250 pixels
    image = Image.new('RGB', (400, 250), color='white')  # Criar uma nova imagem branca
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    
    # Adicionar informações do item acima do código de barras
    text_x = 10
    text_y = 10
    item_info = "Fio Poliester 167/48\nCor: {}\nPeso Liquido: 300g\nLote: F4".format(color)
    lines = item_info.split("\n")
    
    # Desenha o texto acima do código de barras
    for line in lines:
        draw.text((text_x, text_y), line, font=font, fill="black")
        text_y += 15
    
    # Gerar o código de barras
    barcode_image = Image.open(f"{filename}.png")
    barcode_image = barcode_image.resize((400, 150), Image.LANCZOS)
    
    # Posicionar o código de barras abaixo das informações
    barcode_y = text_y + 10
    image.paste(barcode_image, (0, barcode_y))
    
    # Salvar a imagem final
    final_filename = f"{filename}_final.png"
    image.save(final_filename)
    
    # Carregar e exibir a imagem do código de barras na interface
    image = ImageTk.PhotoImage(image)
    barcode_label.config(image=image)
    barcode_label.image = image
    
    # Atualizar a label com a informação
    info_label.config(text=item_info)
    
    # Guardar o código gerado para posterior impressão
    global current_color, current_ean_code
    current_color = color
    current_ean_code = ean_code

def imprimir_codigo():
    quantity = quantity_entry.get()
    if not quantity.isdigit():
        messagebox.showwarning("Input Error", "Por favor, insira uma quantidade válida.")
        return
    
    # Gerar o código ZPL
    zpl = generate_zpl(current_color, current_ean_code, int(quantity))
    
    # Enviar para a impressora
    send_to_printer(zpl)

def generate_zpl(color, ean_code, quantity):
    item_info = "Fio Poliester 167/48\nCor: {}\nPeso Liquido: 300g\nLote: F4".format(color)
    lines = item_info.split("\n")
    
    zpl = "^XA\n"
    for _ in range(quantity):
        zpl += "^FO50,50^A0,30,30^FD{}^FS\n".format(lines[0])
        zpl += "^FO50,90^A0,30,30^FD{}^FS\n".format(lines[1])
        zpl += "^FO50,130^A0,30,30^FD{}^FS\n".format(lines[2])
        zpl += "^FO50,170^A0,30,30^FD{}^FS\n".format(lines[3])
        zpl += "^FO50,210^BY2\n"  # Ajuste o fator de ampliação do código de barras
        zpl += "^BCN,60,Y,N,N\n"  # Altura ajustada para o código de barras
        zpl += "^FD{}^FS\n".format(ean_code)
    zpl += "^XZ"
    
    return zpl

# Configuração da janela principal
root = tk.Tk()
root.title("Gerador de Código de Barras")
root.geometry("900x600")  # Define o tamanho da janela

# Frame para entrada de dados
input_frame = tk.Frame(root)
input_frame.pack(pady=20)

# Campo de entrada para a cor
color_label = tk.Label(input_frame, text="Cor:", width=15, anchor="w")
color_label.grid(row=0, column=0, padx=10, pady=5)
color_entry = tk.Entry(input_frame, width=30)
color_entry.grid(row=0, column=1, padx=10, pady=5)

# Campo de entrada para a quantidade
quantity_label = tk.Label(input_frame, text="Quantidade:", width=15, anchor="w")
quantity_label.grid(row=1, column=0, padx=10, pady=5)
quantity_entry = tk.Entry(input_frame, width=30)
quantity_entry.grid(row=1, column=1, padx=10, pady=5)

# Botão para gerar o código de barras
generate_button = tk.Button(input_frame, text="Gerar Código de Barras", width=20, command=generate_barcode)
generate_button.grid(row=0, column=2, padx=10, pady=5)

# Botão para imprimir o código de barras
print_button = tk.Button(input_frame, text="Imprimir Código de Barras", width=20, command=imprimir_codigo)
print_button.grid(row=1, column=2, padx=10, pady=5)

# Frame para exibir as informações e o código de barras
display_frame = tk.Frame(root)
display_frame.pack(pady=20)

# Label para exibir as informações
info_label = tk.Label(display_frame, text="", justify="left")
info_label.pack()

# Label para exibir o código de barras
barcode_label = tk.Label(display_frame)
barcode_label.pack()

# Função para fechar a conexão com o banco de dados ao fechar a aplicação
def on_closing():
    conn.close()
    root.destroy()

# Configuração para fechar a janela
root.protocol("WM_DELETE_WINDOW", on_closing)

# Iniciar a interface
root.mainloop()
