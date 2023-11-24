import socket
import os
import wave
import json
import pickle
from threading import Thread

# Lista de dispositivos conectados
conectados = []
TAMANHO_BUFFER = 1024 
sockets = {}

# Função para listar os dispositivos conectados
def listar_dispositivos(socket_cliente):
    print('Dispositivos Conectados:')
    for dispositivo in conectados:
        print(f'IP: {dispositivo[0]}, Porta: {dispositivo[1]}')
    socket_cliente.send(pickle.dumps(conectados))

# Função para listar as músicas disponíveis
def listar_musicas(socket_cliente):
    musicas = [musica for musica in os.listdir('music') if musica.endswith(".wav")]
    print('Músicas Disponíveis:')
    for musica in musicas:
        print(musica)
    socket_cliente.send("\n".join(musicas).encode())

# Função para tocar a música no servidor
def tocar_musica_servidor(socket_cliente, escolha_musica):
    if os.path.exists(f"music/{escolha_musica}"):
         with wave.open(f"music/{escolha_musica}", "rb") as arquivo_musica:
            dados = arquivo_musica.readframes(TAMANHO_BUFFER)
            while dados:
                socket_cliente.send(dados)
                dados = arquivo_musica.readframes(TAMANHO_BUFFER)
            socket_cliente.send("\nnn".encode())

# Função para lidar com cada cliente conectado
def lidar_cliente(socket_cliente, endereco_cliente):
    print(f"Conexão estabelecida com o cliente {endereco_cliente}")
    while True:
        requisicao = json.loads(socket_cliente.recv(1024).decode())
        if requisicao['servico'] == 'listar_dispositivos':
            listar_dispositivos(socket_cliente)
        elif requisicao['servico'] == 'listar_musicas':
            listar_musicas(socket_cliente)
        elif requisicao['servico'] == 'tocar_musica':
            musica = requisicao['musica']
            if 'dispositivo' in requisicao:
                ip_dispositivo_alvo = requisicao['dispositivo'][0]
                escolha_musica = musica.encode()
                socket_alvo = sockets[ip_dispositivo_alvo]
                socket_alvo.send(escolha_musica)
            else:
                tocar_musica_servidor(socket_cliente, musica)
        elif requisicao['servico'] == 'encerrar_conexao':
            socket_cliente.close()
            conectados.remove(endereco_cliente)
            print(f"Conexão encerrada com o cliente {endereco_cliente}")
            break

# Função para iniciar o servidor
def iniciar_servidor():
    socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_servidor.bind(('192.168.0.98', 12345))
    socket_servidor.listen(5)
    print("Servidor iniciado. Aguardando conexões...")
    while True:
        socket_cliente, endereco_cliente = socket_servidor.accept()
        sockets[endereco_cliente[0]] = socket_cliente
        conectados.append([endereco_cliente[0],endereco_cliente[1]])
        Thread(target=lidar_cliente, args=(sockets[endereco_cliente[0]], endereco_cliente)).start()

iniciar_servidor()
