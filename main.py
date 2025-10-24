# Bibliotecas utilizadas
import sys
import cv2
from PIL import Image
import os
import requests
import io
import time
import pygame
import google.generativeai as genai
from dotenv import load_dotenv
from langdetect import detect
from deep_translator import GoogleTranslator
import tempfile
import asyncio
import edge_tts

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o mixer do pygame para áudio
pygame.mixer.init()

# Configurações da API do Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Chave da API carregada do ambiente

genai.configure(api_key=GEMINI_API_KEY)

texto_prompt = "Extraia APENAS o texto contido nesta imagem, NADA além disso! Não precisa dizer nada além disso, apenas enviar o texto EXATO sem nenhuma mensagem a mais e nem tentar completar palavras incompletas que terminam a última linha! Não precisa adicionar texto fictício no final!"

documentos = []

video_capture = cv2.VideoCapture(0)  # Alterar este número até achar a porta correspondente da webcam utilizada

custom_config = r'--oem 3 --psm 6'

velocidade = 50  # Velocidade 1.5x


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
            img.save(output, format="JPEG")
            image_bytes = output.getvalue()

        # Carregue o modelo Gemini Vision
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Construa o prompt (incluindo a imagem)
        prompt = texto_prompt
        image_data = {"mime_type": "image/jpeg", "data": image_bytes}

        # Envie a requisição ao modelo
        requisicao = model.generate_content([prompt, image_data])

        # Verifique se a resposta é válida e contém texto
        if requisicao.text and requisicao.text.strip():
            texto = requisicao.text
            documentos.append(texto)
            return texto
        else:
            print("A API não retornou texto válido. Finish reason:", getattr(requisicao, 'finish_reason', 'N/A'))
            return None

    except Exception as e:
        print(f"Erro ao processar a imagem: {e}")
        return None


def play_audio(file_path):
    """Reproduz arquivo de áudio usando pygame"""
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        # Aguarda a reprodução terminar
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        # Para e descarrega a música para liberar o arquivo
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception as e:
        print(f"Erro ao reproduzir áudio: {e}")


async def falar_mensagem_inicial():
    mensagem = "Só um instante, a leitura está sendo processada!"
    communicate = edge_tts.Communicate(mensagem, voice="pt-BR-AntonioNeural", rate="+" + str(velocidade) + "%")
    if not os.path.exists("mensagem_inicial.mp3"):
        await communicate.save("mensagem_inicial.mp3")
    play_audio("mensagem_inicial.mp3")


async def falar_texto(texto):
    # Voz em pt-BR neural e velocidade 1.5x
    start_time = time.time()
    communicate = edge_tts.Communicate(texto, voice="pt-BR-AntonioNeural", rate="+" + str(velocidade) + "%")

    # Cria um arquivo temporário com um nome específico
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = temp_file.name
    temp_file.close()  # Fecha o arquivo para que o edge_tts possa escrever nele

    try:
        await communicate.save(temp_path)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'Tempo (Texto para Audio): {elapsed_time:.2f} segundos')

        start_time = time.time()
        play_audio(temp_path)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'Tempo de reprodução do áudio: {elapsed_time:.2f} segundos')

    finally:
        # Garante que o arquivo seja removido mesmo se houver erro
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            print(f"Aviso: Não foi possível remover o arquivo temporário: {e}")


def traduz(texto, idioma):
    if texto is None:
        return "Não foi possível extrair texto da imagem."

    if idioma == "pt":  # Português
        return texto
    elif idioma == "en":  # Inglês
        tradutor = GoogleTranslator(source='en', target='pt')
        traducao = tradutor.translate(texto)
        return traducao
    elif idioma == "es":  # Espanhol
        tradutor = GoogleTranslator(source='es', target='pt')
        traducao = tradutor.translate(texto)
        return traducao
    else:
        print("Idioma não reconhecido")
        return texto


def responder_pergunta(pergunta):
    model = genai.GenerativeModel("gemini-2.5-flash")
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


def main():
    while True:
        result, img = video_capture.read()
        if result is False:
            break  # Finaliza o loop se ocorrer falha na leitura do frame

        cv2.imshow(
            "BaLeIA - IFPB (Campus Sousa)", img
        )  # Mostra o frame processado em uma janela chamada "BaLeIA - IFPB (Campus Sousa)"

        key = cv2.waitKey(1) & 0xFF

        if key == ord("p"):  # Tira foto e interpreta ela
            if internet_connection():
                asyncio.run(falar_mensagem_inicial())
                start_time = time.time()
                result, img = video_capture.read()
                if result:
                    cv2.imwrite("temp.jpg", img)
                #caminho_imagem = "temp.jpg"
                caminho_imagem = "teste.jpeg"
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
                try:
                    idioma = detect(
                        texto) if texto != "Não foi possível extrair texto desta imagem. Tente novamente com uma imagem mais nítida." else "pt"
                except:
                    idioma = "pt"

                texto = traduz(texto, idioma)
                print(f"{texto}")

                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f'Tempo de tradução do texto (PT, ES e EN): {elapsed_time:.2f} segundos')

                asyncio.run(falar_texto(texto))

                end_time = time.time()
                elapsed_time = end_time - start_time
                print(f'Tempo de processamento da produção do áudio: {elapsed_time:.2f} segundos')
            else:
                if os.path.exists("mensagem_internet.mp3"):
                    play_audio("mensagem_internet.mp3")
                else:
                    print("Sem conexão com a internet")

        if key == ord("q"):  # Finaliza a execução
            if os.path.exists("texto.txt"):
                os.remove("texto.txt")
            break

    # Libera a webcam e fecha as janelas
    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
