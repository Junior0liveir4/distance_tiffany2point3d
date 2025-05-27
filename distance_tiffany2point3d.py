import numpy as np
import matplotlib.pyplot as plt
from is_wire.core import Subscription, Channel
from is_msgs.image_pb2 import Image, ObjectAnnotations
import cv2
import socket

# --- Classe de canal que consome sempre a última mensagem disponível ---
class StreamChannel(Channel):
    def __init__(self, uri="amqp://guest:guest@<ip>:<port>", exchange="is"):
        super().__init__(uri=uri, exchange=exchange)

    def consume_last(self, return_dropped=False):
        dropped = 0
        try:
            msg = super().consume(timeout=0.1)
        except socket.timeout:
            return False

        while True:
            try:
                msg = super().consume(timeout=0.0)
                dropped += 1
            except socket.timeout:
                return (msg, dropped) if return_dropped else msg

# --- Funções auxiliares ---
def msg_verify(msg):
    if isinstance(msg, bool):
        return 'Msg not received'
    return msg.unpack(ObjectAnnotations)

def to_np(input_image):
    if isinstance(input_image, np.ndarray):
        return input_image
    if isinstance(input_image, Image):
        buffer = np.frombuffer(input_image.data, dtype=np.uint8)
        return cv2.imdecode(buffer, flags=cv2.IMREAD_COLOR)
    return np.array([], dtype=np.uint8)

def undistort_and_crop(frame, K, dist, nK, roi):
    undistorted = cv2.undistort(frame, K, dist, None, nK)
    x, y, w, h = roi
    return undistorted[0:h, 0:w]

def project_point(P, point3d):
    homog_point = np.vstack((point3d, [1]))
    proj = P @ homog_point
    proj /= proj[2, 0]
    return int(proj[0, 0]), int(proj[1, 0])

# --- Parâmetros e subscrição dos tópicos ---
camera_ids = [1, 2, 3, 4]
broker_uri = "amqp://rabbitmq:30000"

channel = StreamChannel(broker_uri)
subscription = Subscription(channel)
for cam_id in camera_ids:
    subscription.subscribe(f"CameraGateway.{cam_id}.Frame")
    subscription.subscribe(f"Tiffany.{cam_id}.Detection")

# --- Leitura dos parâmetros de calibração ---
calib = {}
P = {}
for i in camera_ids:
    data = np.load(f"/homes/joliveira/Desktop/Junior/Códigos/distance_tiffany2point3d/matrix_cams/calib_rt{i}.npz")
    calib[i] = {key: data[key] for key in ['K', 'dist', 'nK', 'roi', 'rt']}
    P[i] = calib[i]['nK'] @ calib[i]['rt']

# --- Função para selecionar ponto clicado ---
def get_click_or_skip(image, cam_id):
    fig, ax = plt.subplots(figsize=(25, 20))
    ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title(f"Câmera {cam_id}: clique para selecionar ou pressione 'q' para pular")
    coords = []
    skip_flag = {'skip': False}

    def on_click(event):
        if event.key == 'q':
            skip_flag['skip'] = True
            plt.close()
        elif event.xdata and event.ydata:
            coords.append(np.array([[int(event.xdata)], [int(event.ydata)], [1]]))
            print(f"[INFO] Câmera {cam_id}: ponto selecionado: ({int(event.xdata)}, {int(event.ydata)})")
            plt.close()

    def on_scroll(event):
        if event.xdata is None or event.ydata is None:
            return
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        zoom = 1.1 if event.button == 'up' else 0.9
        ax.set_xlim([event.xdata - (event.xdata - xlim[0]) * zoom,
                     event.xdata + (xlim[1] - event.xdata) * zoom])
        ax.set_ylim([event.ydata - (event.ydata - ylim[0]) * zoom,
                     event.ydata + (ylim[1] - event.ydata) * zoom])
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', on_click)
    fig.canvas.mpl_connect('key_press_event', on_click)
    fig.canvas.mpl_connect('scroll_event', on_scroll)
    plt.tight_layout()
    plt.show()

    if skip_flag['skip']:
        print(f"[INFO] Câmera {cam_id}: ponto ignorado com 'q'")
        return None
    return coords[0] if coords else None

# --- Seleção de pontos 2D nas imagens ---
clicked_points = {}
for cam_id in camera_ids:
    print(f"[INFO] Aguardando imagem da câmera {cam_id}...")
    while True:
        msg = channel.consume()
        if msg.topic == f"CameraGateway.{cam_id}.Frame":
            try:
                img = msg.unpack(Image)
                frame = undistort_and_crop(to_np(img), *[calib[cam_id][k] for k in ['K', 'dist', 'nK', 'roi']])
                ponto = get_click_or_skip(frame, cam_id)
                if ponto is not None:
                    clicked_points[cam_id] = ponto
                break
            except Exception as e:
                print(f"[ERRO] Falha ao processar imagem da câmera {cam_id}: {e}")

# --- Triangulação 3D do ponto objetivo ---
if len(clicked_points) < 2:
    print("[ERRO] Pelo menos dois pontos são necessários para triangulação.")
    exit()

A = np.vstack([np.hstack((P[i], -clicked_points[i])) for i in clicked_points])
_, _, Vt = np.linalg.svd(A)
X = Vt[-1]
ponto_objetivo = (X[:3] / X[3]).reshape(3, 1)
print(f"🎯 Ponto 3D (objetivo):\n{ponto_objetivo}\n")

# --- Subscrição dos tópicos de detecção e imagem da câmera 1 ---
subscriptions = {}
for i in camera_ids:
    ch = StreamChannel(broker_uri)
    sub = Subscription(ch)
    sub.subscribe(f"Tiffany.{i}.Detection")
    subscriptions[i] = (ch, sub)

cam_channel = StreamChannel(broker_uri)
cam_sub = Subscription(cam_channel)
for i in camera_ids:
    cam_sub.subscribe(f"CameraGateway.{i}.Frame")

plt.ion()  # Ativa modo interativo
fig, ax = plt.subplots(figsize=(20, 16))  # Ajustar o tamanho da janela de visualização
img_plot = None

camera_id = 1

def on_key(event):
    global camera_id
    if event.key == 'up':
        camera_id = camera_id + 1 if camera_id < 4 else 1
    elif event.key == 'down':
        camera_id = camera_id - 1 if camera_id > 1 else 4
    print(f"[INFO] Visualizando Câmera {camera_id}")

fig.canvas.mpl_connect('key_press_event', on_key)

while True:
    frames = {i: msg_verify(subscriptions[i][0].consume_last()) for i in camera_ids}
    us = [np.array([[0], [0], [2]]) for _ in camera_ids]
    cams_detected = []

    for i in camera_ids:
        if isinstance(frames[i], str):
            continue
        try:
            v1, v2 = frames[i].objects[0].region.vertices[0], frames[i].objects[0].region.vertices[1]
            cx, cy = (v1.x + v2.x) / 2, (v1.y + v2.y) / 2
            pt = np.array([[[cx, cy]]], dtype=np.float32)
            undist_pt = cv2.undistortPoints(pt, calib[i]['K'], calib[i]['dist'], P=calib[i]['nK'])
            us[i - 1] = np.array([[undist_pt[0][0][0]], [undist_pt[0][0][1]], [1]])
            cams_detected.append(i)
        except:
            continue

    msg_cam = cam_channel.consume_last()
    if msg_cam and msg_cam.topic == f"CameraGateway.{camera_id}.Frame":
        img = msg_cam.unpack(Image)
        frame = to_np(img)
        K_vis = calib[camera_id]['K']
        dist_vis = calib[camera_id]['dist']
        roi_vis = calib[camera_id]['roi']
        nK_vis = calib[camera_id]['nK']
        P_vis = nK_vis @ calib[camera_id]['rt']

        dst = undistort_and_crop(frame, K_vis, dist_vis, nK_vis, roi_vis)

        tiff_xy = (int(us[camera_id - 1][0, 0]), int(us[camera_id - 1][1, 0]))
        cv2.circle(dst, tiff_xy, 5, (0, 0, 255), -1)  # Tiffany

        proj_obj = project_point(P_vis, ponto_objetivo)
        cv2.circle(dst, proj_obj, 5, (255, 0, 0), -1)  # Objetivo

        cv2.arrowedLine(dst, tiff_xy, proj_obj, (0, 0, 0), 2, tipLength=0.1)

        dst_rgb = cv2.cvtColor(dst, cv2.COLOR_BGR2RGB)

        # Atualiza a imagem no matplotlib
        if img_plot is None:
            img_plot = ax.imshow(dst_rgb)
            plt.title("Localização da Tiffany")
            plt.axis("off")
        else:
            img_plot.set_data(dst_rgb)
        plt.pause(0.001)  # Atualiza a janela sem travar o loop

    if len(cams_detected) > 1:
        A = np.zeros((3 * len(cams_detected), 4 + len(cams_detected)))
        for idx, cam in enumerate(cams_detected):
            A[3*idx:3*idx+3, 0:4] = P[cam]
            A[3*idx:3*idx+3, 4 + idx] = -us[cam - 1].ravel()

        _, _, Vt = np.linalg.svd(A)
        sol = Vt[-1].reshape(-1, 1)
        sol /= sol[3]
        pnt_3d = np.round(sol[0:3], 2)

        print("Posição:", pnt_3d)
        vetor = ponto_objetivo - pnt_3d
        print("Vetor de distância:", vetor)
        erro = np.linalg.norm(vetor)
        print("Módulo do erro:", round(erro, 2))
        angulo_rad = np.arctan2(vetor[1], vetor[0])
        print("Ângulo: {:.2f}".format(np.degrees(angulo_rad[0])))

plt.ioff()
plt.close()
