import os
import sys
import subprocess
sys.stdout.reconfigure(encoding='utf-8')

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.insert(0, os.path.abspath(os.path.join(__dir__, '../..')))

os.environ["FLAGS_allocator_strategy"] = 'auto_growth'

import cv2
import copy
import numpy as np
import json
import time
import logging
from PIL import Image
import utility_vn as utility
import predict_rec_vn as predict_rec
import predict_det_vn as predict_det
import predict_cls_vn as predict_cls
from PaddleOCR.ppocr.utils.utility import get_image_file_list, check_and_read
from PaddleOCR.ppocr.utils.logging import get_logger
from utility_vn import draw_ocr_box_txt, get_rotate_crop_image, get_minarea_rect_crop
from gtts import gTTS
from playsound import playsound
logger = get_logger()


class TextSystem(object):
    def __init__(self, args):
        if not args.show_log:
            logger.setLevel(logging.INFO)

        self.text_detector = predict_det.TextDetector(args)
        self.text_recognizer = predict_rec.TextRecognizer(args)
        self.use_angle_cls = args.use_angle_cls
        self.drop_score = args.drop_score
        if self.use_angle_cls:
            self.text_classifier = predict_cls.TextClassifier(args)

        self.args = args
        self.crop_image_res_index = 0

    def draw_crop_rec_res(self, output_dir, img_crop_list, rec_res):
        os.makedirs(output_dir, exist_ok=True)
        bbox_num = len(img_crop_list)
        for bno in range(bbox_num):
            cv2.imwrite(
                os.path.join(output_dir,
                             f"mg_crop_{bno+self.crop_image_res_index}.jpg"),
                img_crop_list[bno])
            logger.debug(f"{bno}, {rec_res[bno]}")
        self.crop_image_res_index += bbox_num

    def __call__(self, img, cls=True):
        time_dict = {'det': 0, 'rec': 0, 'csl': 0, 'all': 0}
        start = time.time()
        ori_im = img.copy()
        dt_boxes, elapse = self.text_detector(img)
        time_dict['det'] = elapse
        logger.debug("dt_boxes num : {}, elapse : {}".format(
            len(dt_boxes), elapse))
        if dt_boxes is None:
            return None, None
        img_crop_list = []

        dt_boxes = sorted_boxes(dt_boxes)

        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            if self.args.det_box_type == "quad":
                img_crop = get_rotate_crop_image(ori_im, tmp_box)
            else:
                img_crop = get_minarea_rect_crop(ori_im, tmp_box)
            img_crop_list.append(img_crop)
        if self.use_angle_cls and cls:
            img_crop_list, angle_list, elapse = self.text_classifier(
                img_crop_list)
            time_dict['cls'] = elapse
            logger.debug("cls num  : {}, elapse : {}".format(
                len(img_crop_list), elapse))

        rec_res, elapse = self.text_recognizer(img_crop_list)
        time_dict['rec'] = elapse
        logger.debug("rec_res num  : {}, elapse : {}".format(
            len(rec_res), elapse))
        if self.args.save_crop_res:
            self.draw_crop_rec_res(self.args.crop_res_save_dir, img_crop_list,
                                   rec_res)
        filter_boxes, filter_rec_res = [], []
        for box, rec_result in zip(dt_boxes, rec_res):
            text, score = rec_result
            if score >= self.drop_score:
                filter_boxes.append(box)
                filter_rec_res.append(rec_result)
        end = time.time()
        time_dict['all'] = end - start
        return filter_boxes, filter_rec_res, time_dict


def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)

    for i in range(num_boxes - 1):
        for j in range(i, -1, -1):
            if abs(_boxes[j + 1][0][1] - _boxes[j][0][1]) < 10 and \
                    (_boxes[j + 1][0][0] < _boxes[j][0][0]):
                tmp = _boxes[j]
                _boxes[j] = _boxes[j + 1]
                _boxes[j + 1] = tmp
            else:
                break
    return _boxes


def main(args, text_sys):
    image_file_list = get_image_file_list("./camera/frame.jpg")
    image_file_list = image_file_list[args.process_id::args.total_process_num]
    font_path = args.vis_font_path
    drop_score = args.drop_score
    draw_img_save_dir = args.draw_img_save_dir
    os.makedirs(draw_img_save_dir, exist_ok=True)
    save_results = []

    total_time = 0
    cpu_mem, gpu_mem, gpu_util = 0, 0, 0
    _st = time.time()
    count = 0
    for idx, image_file in enumerate(image_file_list):

        img, flag_gif, flag_pdf = check_and_read(image_file)
        if not flag_gif and not flag_pdf:
            img = cv2.imread(image_file)
        if not flag_pdf:
            if img is None:
                logger.debug("error in loading image:{}".format(image_file))
                continue
            imgs = [img]
        else:
            page_num = args.page_num
            if page_num > len(img) or page_num == 0:
                page_num = len(img)
            imgs = img[:page_num]
        for index, img in enumerate(imgs):
            starttime = time.time()
            dt_boxes, rec_res, time_dict = text_sys(img)
            elapse = time.time() - starttime
            total_time += elapse
            if len(imgs) > 1:
                logger.debug(
                    str(idx) + '_' + str(index) + "  Predict time of %s: %.3fs"
                    % (image_file, elapse))
            else:
                logger.debug(
                    str(idx) + "  Predict time of %s: %.3fs" % (image_file,
                                                                elapse))
            # for text, score in rec_res:
            #     logger.debug("{}, {:.3f}".format(text, score))

            # res = [{
            #     "transcription": rec_res[i][0],
            #     "points": np.array(dt_boxes[i]).astype(np.int32).tolist(),
            # } for i in range(len(dt_boxes))]
            res = [rec_res[i][0] for i in range(len(dt_boxes))]
            if len(imgs) > 1:
                save_pred = os.path.basename(image_file) + '_' + str(
                    index) + "\t" + json.dumps(
                        res, ensure_ascii=False) + "\n"
            else:
                save_pred = json.dumps(
                    res, ensure_ascii=False) + "\n"
            save_results.append(save_pred)

    logger.info("The predict total time is {}".format(time.time() - _st))
    # if args.benchmark:
    #     text_sys.text_detector.autolog.report()
    #     text_sys.text_recognizer.autolog.report()

    with open(
            os.path.join(draw_img_save_dir, "system_results.txt"),
            'w',
            encoding='utf-8') as f:
        f.writelines(save_results)

def read_aloud(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        text = file.read()

    language = 'vi'

    # # Create audio file
    tts = gTTS(text = text, lang=language)
    tts.save('output.mp3')

    # # #Play audio file
    playsound('output.mp3')
    os.remove('output.mp3')

if __name__ == "__main__":
    args = utility.parse_args()
    record = True
    text_sys = TextSystem(args)
    cap = cv2.VideoCapture(0)
    while True:
        #Capture a frame from the camera
        ret, frame = cap.read()

        # Show the frame on the screen
        cv2.imshow("Video", frame)

        key = cv2.waitKey(10)

        #Check if 3 second have passed
        if key == ord('c'):
            # Save the frame to a file
            cv2.imwrite("./camera/frame.jpg", frame)
            main(args, text_sys)
            with open('./inference_results/system_results.txt', 'r', encoding='utf-8') as f:
                words = json.load(f)

            lowercase_words = [word.lower() for word in words]

            with open('output.txt', mode = 'w', encoding='utf-8') as file:
            #Write each lowercased word to the file
                for word in lowercase_words:
                    file.write(word + ' ')

            filename = 'output.txt'
            read_aloud(filename)
        
        if key == ord('q'):
            record = False
        
        if not record:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    
