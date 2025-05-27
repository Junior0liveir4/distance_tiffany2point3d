
# 🐾📍 Distance_Tiffany2Point3D – Localização 3D e Distância da Tiffany

Este projeto realiza a reconstrução da posição 3D do robô **Tiffany** (desenvolvido pelo Lab Penguin) com base na detecção de sua bounding box em múltiplas câmeras, e calcula a distância até um ponto fixo selecionado pelo usuário. Foi desenvolvido para **ambiente local**, utilizando conceitos avançados de **visão computacional** e comunicação via **RabbitMQ (IS framework)** no ambiente do **LabSEA (IFES Guarapari)**.

---

## 🎯 Objetivos

- Corrigir a distorção das imagens de múltiplas câmeras com base em parâmetros de calibração.
- Permitir a seleção de um ponto fixo no ambiente através de cliques em imagens de pelo menos 2 câmeras.
- Reconstruir a posição 3D do robô Tiffany com base nas coordenadas de detecção em múltiplas câmeras.
- Calcular e exibir a **distância**, **vetor de deslocamento**, e o **ângulo** entre o ponto fixo e Tiffany.
- Visualizar o resultado com uma **seta gráfica** apontando da Tiffany para o ponto fixo.

---

## 🧠 Conceitos aplicados

- 📷 **Calibração de câmeras**: uso das matrizes `K`, `dist`, `nK`, `roi` e `rt` para remoção de distorção e projeção 3D.
- 🎯 **Triangulação 3D**: reconstrução da posição no espaço a partir de múltiplas visualizações 2D.
- 🦾 **Detecção de objetos**: uso das mensagens `ObjectAnnotations` para localizar Tiffany.
- 📐 **Transformações de coordenadas e álgebra linear**: uso de SVD para triangulação, cálculo vetorial e de ângulos.
- 🖼️ **Visualização interativa com matplotlib e OpenCV**: seleção de pontos, exibição de setas e círculos.

---

## ⚙️ Requisitos

Instale as dependências com:

```bash
pip install numpy matplotlib opencv-python is-wire is-msgs
```

---

## 📂 Estrutura esperada

```
distance_tiffany2point3d/
├── distance_tiffany2point3d.py
├── matrix_cams/
│   ├── calib_rt1.npz
│   ├── calib_rt2.npz
│   ├── calib_rt3.npz
│   └── calib_rt4.npz
```

Os arquivos `.npz` devem conter:
- `K`: matriz intrínseca
- `dist`: coeficientes de distorção
- `nK`: nova matriz intrínseca para visualização sem distorção
- `roi`: região de interesse para recorte
- `rt`: matriz extrínseca (rotação + translação)

---

## 🚀 Como usar

1. Certifique-se de que o broker RabbitMQ está ativo e que os gateways das 4 câmeras estão publicando em:

```
CameraGateway.{id}.Frame
Tiffany.{id}.Detection
```

2. Execute o script:

```bash
python3 distance_tiffany2point3d.py
```

3. Para cada câmera, uma imagem será exibida e o usuário poderá clicar para definir um ponto fixo no ambiente.
   - Pressione `q` para pular uma câmera.
   - Pelo menos 2 câmeras devem ter o ponto selecionado.

4. Após a seleção:
   - A posição 3D do ponto fixo será triangulada.
   - Tiffany será localizada automaticamente com base nas detecções.
   - A posição 3D de Tiffany será calculada em tempo real.
   - A seta será desenhada do robô para o ponto fixo.
   - O **vetor**, **módulo da distância** e **ângulo** serão mostrados no terminal.

---

## 📺 Controles

- Use as **setas ↑ e ↓ do teclado** para alternar entre as câmeras exibidas na visualização principal.
- O sistema exibe em tempo real a:
  - Localização da Tiffany (círculo vermelho)
  - Ponto fixo escolhido (círculo azul)
  - Vetor de distância (seta preta)

---

## 💡 Exemplo de saída no terminal

```
🎯 Ponto 3D (objetivo):
[[ 1.24]
 [ 0.75]
 [ 0.30]]

Posição: [[1.52]
 [0.88]
 [0.29]]
Vetor de distância: [[-0.28]
 [-0.13]
 [ 0.01]]
Módulo do erro: 0.31
Ângulo: -154.34
```

---

## 🧪 O que o código faz

- Conecta-se ao broker AMQP do LabSEA.
- Subscrições:
  - `CameraGateway.{id}.Frame` (imagens)
  - `Tiffany.{id}.Detection` (bounding boxes)
- Aplica `cv2.undistort` com os parâmetros de calibração.
- Usa SVD para triangulação 3D de pontos.
- Converte vértices das bounding boxes em coordenadas 3D.
- Calcula a distância Euclidiana e ângulo no plano XY.
- Exibe visualmente a cena e as projeções.

---

## 🖥️ Visualização

- Visualização feita com `matplotlib`, com atualização em tempo real.
- Utiliza `cv2.arrowedLine`, `cv2.circle` e conversão de cores BGR→RGB.

---

## 📬 Contato

Para dúvidas ou sugestões, entre em contato com o time do LabSEA.
