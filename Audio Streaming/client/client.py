import socket
import pyaudio
import os
import json
import pickle
import threading

# Definindo constantes para o áudio
TAMANHO_BUFFER = 1024
CANAL = 2
FORMATO = pyaudio.paInt16
TAXA = 44100
pausado = False
terminado = False

# Função para listar os dispositivos conectados
def listar_dispositivos(socket_cliente):
    msg = {'servico':'listar_dispositivos'}
    msg_bytes = json.dumps(msg).encode('utf-8')
    socket_cliente.send(msg_bytes)
    dispositivos = socket_cliente.recv(TAMANHO_BUFFER)
    lista_dispositivos = pickle.loads(dispositivos)
    return lista_dispositivos
    
# Função para listar as músicas disponíveis
def listar_musicas(socket_cliente):
    msg = {'servico':'listar_musicas'}
    msg_bytes = json.dumps(msg).encode('utf-8')
    socket_cliente.send(msg_bytes)
    lista_musicas = socket_cliente.recv(TAMANHO_BUFFER).decode()
    print("Lista de músicas disponíveis:")
    print("-----------------------------------------------")
    print(lista_musicas)
    print("-----------------------------------------------")

# Função para tocar a música no servidor
def tocar_musica_servidor(socket_cliente, escolha_musica, dispositivo = None):
    global pausado, terminado
    
    if not os.path.exists(f"music/{escolha_musica}"):
        print(f"A música {escolha_musica} não existe no servidor.")
        return
    
    if dispositivo:
        msg = {'servico': 'tocar_musica', 'musica': f'{escolha_musica}','dispositivo':dispositivo}
        msg_bytes = json.dumps(msg).encode('utf-8')
    else:
        msg = {'servico': 'tocar_musica', 'musica': f'{escolha_musica}'}
        msg_bytes = json.dumps(msg).encode('utf-8')
    socket_cliente.send(msg_bytes)
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMATO, channels=CANAL, rate=TAXA, frames_per_buffer=TAMANHO_BUFFER, output=True)
    dados_arquivo = b''
    mensagem_final = b'\nnn'
    while True:
        if not pausado:
            dados = socket_cliente.recv(TAMANHO_BUFFER)
            dados_arquivo += dados
            if dados[-3:] == mensagem_final: # Verificando a última trinca de bytes da música.
                terminado = True 
                break
            stream.write(dados)
        else:
            continue

    if os.path.isdir("cache") == False:
        os.makedirs("cache")

    if len(dados_arquivo) != 0:
        arquivo = open(f'cache/{escolha_musica}', 'wb')
        arquivo.write(dados_arquivo)
        arquivo.close()

    stream.stop_stream()
    stream.close()

# Função para tocar a música do cache
def tocar_musica_cache(escolha_musica):
     # Verifica se a música existe no servidor
    if not os.path.exists(f"music/{escolha_musica}"):
        print(f"A música {escolha_musica} não existe.")
        return
    global pausado, terminado
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMATO, channels=CANAL, rate=TAXA, output=True)
    print("Reproduzindo do cache...")
    with open(f'cache/{escolha_musica}', 'rb') as arquivo:
        while True:
            if not pausado:
                dados = arquivo.read(TAMANHO_BUFFER)
                stream.write(dados)
            if not dados:
                terminado = True
                break

# Função para lidar com a entrada do usuário
def lidar_entrada_usuario():
    global pausado, terminado

    while not terminado:
        comando = input("Digite 1 para pausar ou 2 para retomar a reprodução: ")
        if comando == '1':
            pausado = True
            print("Reprodução pausada.")
        elif comando == '2':
            pausado = False
            print("Reprodução retomada.")
            
        else:
            print("Comando inválido.")
    print("Reprodução concluída.")
    terminado = False
    pausado = False

# Função para encerrar a conexão
def encerrar_conexao(socket_cliente):
    msg = {'servico': 'encerrar_conexao'}
    msg_bytes = json.dumps(msg).encode('utf-8')
    socket_cliente.send(msg_bytes)
    socket_cliente.close()

def iniciar_cliente():
    socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_cliente.connect(("192.168.0.98", 12345))
    endereco_socket = socket_cliente.getsockname()
    print(endereco_socket)


    while True:
        print("--------------------------------------------------------------------------------------------------")
        comando = input('1 - Listar dispositivos disponíveis\n2 - Listar músicas disponíveis\n3 - Tocar Música\n4 - Ficar disponível para reproduzir músicas\n5 - Encerrar Conexão\n')
        print("--------------------------------------------------------------------------------------------------")
        if comando == '1':
            dispositivos = listar_dispositivos(socket_cliente)
            print("---------------------------------------")
            for i, dispositivo in enumerate(dispositivos):
                print(f"{i} - Host: {dispositivo[0]}, PORT: {dispositivo[1]}")
            print("---------------------------------------")
        elif comando == '2':
            listar_musicas(socket_cliente)
        elif comando == '3':
            while True:
                escolha_musica = input("Digite o nome da música que deseja reproduzir: ")
                if os.path.exists(f"music/{escolha_musica}"):
                    break
                else:
                    print(f"A música {escolha_musica} não existe no servidor. Tente novamente.")

            dispositivos = listar_dispositivos(socket_cliente)
            for i, dispositivo in enumerate(dispositivos):
                print(f"{i} - Host:{dispositivo[0]}, Port:{dispositivo[1]}")

            escolha_dispositivo = int(input("Digite o índice do dispositivo que deseja reproduzir. "))

            if dispositivos[escolha_dispositivo][0] == endereco_socket[0] and dispositivos[escolha_dispositivo][1] == endereco_socket[1]:
                if os.path.isdir("cache"):
                    musicas_cache = os.listdir('cache')
                    if escolha_musica in musicas_cache:
                        thread_tocar_musica = threading.Thread(target=tocar_musica_cache, args=(escolha_musica,), daemon=True)
                        thread_tocar_musica.start()
                        lidar_entrada_usuario()
                    else:
                        print("Música não encontrada na lista de cache local, transmitindo pelo servidor...")
                        thread_tocar_musica = threading.Thread(target=tocar_musica_servidor, args=(socket_cliente, escolha_musica,), daemon=True)
                        thread_tocar_musica.start()
                        lidar_entrada_usuario()
                else:
                    print("Música não encontrada na lista de cache local, transmitindo pelo servidor...")
                    thread_tocar_musica = threading.Thread(target=tocar_musica_servidor, args=(socket_cliente, escolha_musica,), daemon=True)
                    thread_tocar_musica.start()
                    lidar_entrada_usuario()
            else:
                print(f"Reproduzindo no dispositivo {escolha_dispositivo}...")
                thread_tocar_musica = threading.Thread(target=tocar_musica_servidor, args=(socket_cliente, escolha_musica, dispositivos[escolha_dispositivo],), daemon=True)
                thread_tocar_musica.start()
                lidar_entrada_usuario()
        elif comando == '4':
            escolha_musica = input("Digite o nome da música que deseja reproduzir: ")
            while not os.path.exists(f"recursos/{escolha_musica}"):
                print(f"A música {escolha_musica} não existe no servidor. Tente novamente.")
                escolha_musica = input("Digite o nome da música que deseja reproduzir: ")

            print(f"Reproduzindo {escolha_musica}... ")
            tocar_musica_servidor(socket_cliente, escolha_musica)
            lidar_entrada_usuario()
        elif comando == '5':
            encerrar_conexao(socket_cliente)
            break

iniciar_cliente()

