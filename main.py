# Bibliotecas utilizadas
import sys
import cv2
from PIL import Image
import os
import requests
import io
import gtts
import time
from playsound import playsound
from pydub import AudioSegment
import google.generativeai as genai
from dotenv import load_dotenv
from langdetect import detect
from deep_translator import GoogleTranslator
import tempfile
import asyncio
import edge_tts
import speech_recognition as sr
import platform

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria um reconhecedor de fala
recognizer = sr.Recognizer()

# Configurações da API do Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Chave da API carregada do ambiente

genai.configure(api_key=GEMINI_API_KEY)

texto_prompt = "Extraia APENAS o texto contido nesta imagem, NADA além disso! Não precisa dizer nada além disso, apenas enviar o texto EXATO sem nenhuma mensagem a mais e nem tentar completar palavras incompletas que terminam a última linha! Não precisa adicionar texto fictício no final!"

documentos = []

video_capture = cv2.VideoCapture(0) #Alterar este número até achar a porta correspondente da webcam utilizada

custom_config = r'--oem 3 --psm 6'

velocidade = 50 # Velocidade 1.5x

def internet_connection():
    try:

        response = requests.get("https://www.google.com", timeout=5)

        return True

    except requests.ConnectionError:

        return False

def resize(image_path, largura, altura, quality):

    imagem = Image.open(image_path)

    imagem.thumbnail((largura, altura))

    imagem.save("temp_resize.jpg", quality=quality)

    return Image.open("temp_resize.jpg")

# Acessa o Gemini e pede para interpretar a imagem enviada transformando em texto
def extrai_texto_da_imagem(image_path):
    try:
        # Carregue a imagem

        img = resize(image_path, 800, 600, 50)

        # Converta a imagem para bytes (formato esperado pela API Gemini)
        with io.BytesIO() as output:
            img.save(output, format="JPEG")  # Ou PNG, dependendo da imagem
            image_bytes = output.getvalue()

        # Carregue o modelo Gemini Vision (gemini-pro-vision)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Construa o prompt (incluindo a imagem)
        prompt = texto_prompt
        image_data = {"mime_type": "image/jpeg", "data": image_bytes}  # Ajuste o tipo MIME se necessário

        # Envie a requisição ao modelo
        requisicao = model.generate_content([prompt, image_data])

        # Obtenha o texto da resposta
        texto = requisicao.text

        documentos.append(texto)

        return texto

    except Exception as e:

        print(f"Erro ao processar a imagem: {e}")

        return None


async def falar_mensagem_inicial():
    mensagem = "Só um instante, a leitura está sendo processada!"
    communicate = edge_tts.Communicate(mensagem, voice="pt-BR-AntonioNeural", rate="+" + str(velocidade) + "%")
    if not os.path.exists("mensagem_inicial.mp3"):
        await communicate.save("mensagem_inicial.mp3")
    playsound("mensagem_inicial.mp3")


async def falar_texto(texto):
    # Voz em pt-BR neural e velocidade 1.5x
    start_time = time.time()
    communicate = edge_tts.Communicate(texto, voice="pt-BR-AntonioNeural", rate="+" + str(velocidade) + "%")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        await communicate.save(f.name)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'Tempo (Texto para Audio): {elapsed_time:.2f} segundos')
        start_time = time.time()
        playsound(f.name)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'Tempo de reprodução do áudio: {elapsed_time:.2f} segundos')
        os.remove(f.name)


def traduz(texto, idioma):
    if idioma == "pt": #Português
        return texto

    elif idioma == "en": #Inglês
        tradutor = GoogleTranslator(source='en', target='pt')
        traducao = tradutor.translate(texto)
        return traducao

    elif idioma == "es": #Espanhol
        tradutor = GoogleTranslator(source='es', target='pt')
        traducao = tradutor.translate(texto)
        return traducao

    else:
        print("Idioma não reconhecido")
        return texto


def responder_pergunta(pergunta):

    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        with open("texto.txt", 'r') as arquivo:
            conteudo_arquivo = arquivo.read()

            # Criar o prompt com o arquivo e a pergunta
            prompt = [conteudo_arquivo, pergunta]

            # Gerar a resposta
            resposta = model.generate_content(prompt)

            return resposta.text.strip()

    except FileNotFoundError:
        return "Erro: Arquivo não encontrado."
    except Exception as e:
        return f"Erro ao processar o texto: {e}"


def fazer_perguntas_voz():

    conteudo = "".join(documentos)

    while True:

        playsound("mensagem_duvida.mp3")

        # Usa o microfone como fonte de áudio
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)  # Ajusta para o ruído ambiente
            playsound("beep.mp3")
            audio = recognizer.listen(source)  # Escuta o que foi falado

        try:
            # Reconhece a fala usando o Google Web Speech API (configurado para português do Brasil)
            pergunta = recognizer.recognize_google(audio, language="pt-BR")
            pergunta_final = "Responda em português do Brasil sem tags de negrito: " + pergunta
            print(pergunta_final)
            resposta = responder_pergunta(pergunta_final)
            print(f"Pergunta: {pergunta}\nResposta: {resposta}\n")
            asyncio.run(falar_texto(resposta))

        except sr.UnknownValueError:
            print("Não consegui entender o áudio.")
            playsound("mensagem_fim_duvida.mp3")
            return

        except sr.RequestError:
            print("Não foi possível acessar o serviço de reconhecimento de fala.")


def fazer_perguntas_texto():

    while True:
        pergunta = input("Digite a pergunta: ")
        resposta = responder_pergunta(pergunta)
        print(f"Resposta: {resposta}\n")


def main():

    while True:

        result, img = video_capture.read()

        if result is False:
            break  # Finaliza o loop se ocorrer falha na leitura do frame

        cv2.imshow(
            "BaLeIA - IFPB (Campus Sousa)", img
        )  # Mostra o frame processado em uma janela chamada "BaLeIA - IFPB (Campus Sousa)"

        key = cv2.waitKey(1) & 0xFF

        if key == ord("p"): # Tira foto e interpreta ela
            if internet_connection():
                asyncio.run(falar_mensagem_inicial())
                start_time = time.time()
                result, img = video_capture.read()
                if result:
                    cv2.imwrite("temp.jpg", img)
                #caminho_imagem = "teste.jpeg"
                #caminho_imagem = "leitura.jpg"
                caminho_imagem = "temp.jpg"
                texto = extrai_texto_da_imagem(caminho_imagem)
                texto = texto.replace("\n", " ")
                with open('texto.txt', 'w', encoding='utf-8') as arquivo:
                    arquivo.write(texto)
                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f'Tempo (Imagem para Texto): {elapsed_time:.2f} segundos')
                if os.path.exists("temp.jpg"):
                    os.remove("temp.jpg")
                if os.path.exists("temp_resize.jpg"):
                    os.remove("temp_resize.jpg")
                start_time = time.time()
                idioma = detect(texto)
                texto = traduz(texto, idioma)
                print(f"{texto}")
                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f'Tempo de tradução do texto (PT, ES e EN): {elapsed_time:.2f} segundos')
                asyncio.run(falar_texto(texto))
                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f'Tempo de processamento da produção do áudio: {elapsed_time:.2f} segundos')
                fazer_perguntas_voz()
            else:
                playsound("mensagem_internet.mp3")

        if key == ord("q"): # Finaliza a execução
            #if os.path.exists("texto.txt"):
                #os.remove("texto.txt")
            break

if __name__ == "__main__":
    main()