# -*- coding: utf-8 -*-

import threading
import tkinter as Tk
import cv2
import numpy as np

from data_ref import CATALOGUE, CLASS_TEST

remaining_students = []


def get_contours_topology(image):
    """
    Принимает в качестве параметра цветное изображение в формате RGB и возвращает:
     - список обнаруженных контуров
     - их топология (дерево включений)
     - изображение преобразовано в уровень серого
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 1000)
    ced_image = cv2.Canny(blurred, 50, 180)
    cv2.imshow('canny', ced_image)
    contours, hierarchy = cv2.findContours(ced_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return contours, hierarchy, gray


def edging(contour):
    """
    Принимает в качестве параметра массив точек и возвращает
    массив вершин прямоугольника, наилучшим образом обрамляющий контур.
    """
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.intp(box)
    angle = rect[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90

    if angle == 0:
        min_index = np.argmin(box[:, 0])
    elif angle == 90:
        min_index = np.argmin(box[:, 1])
    else:
        min_index = np.argmin(box[:, 0] + box[:, 1])
    box = np.roll(box, -min_index, axis=0)

    return [box]


def extract_identifier(im_gray, box, image_display, group=CLASS_TEST):
    """
     Принимает в качестве параметра изображение в оттенке серого
     и прямоугольник в виде массива вершин, который должен обрамлять карточку.
     Пишет на отображаемом изображении ответ ученика, который владеет карточкой.
     Возвращает целое число, идентифицирующее карточку.
    """
    str_code = ''
    tops = [tuple(top) for top in box[0]]
    x_min = min(tops, key=lambda t: t[0])[0]
    x_max = max(tops, key=lambda t: t[0])[0]
    y_min = min(tops, key=lambda t: t[1])[1]
    y_max = max(tops, key=lambda t: t[1])[1]
    if x_max > x_min and y_max > y_min:
        zone = im_gray[y_min:y_max, x_min:x_max]
        depart = np.float32(tuple(map(lambda t: (t[0] - x_min, t[1] - y_min), tops[:3])))
        purpose = np.float32(((0, 0), (200, 0), (200, 200)))
        mat = cv2.getAffineTransform(depart, purpose)

        straightened_area = cv2.warpAffine(zone, mat, (200, 200))
        contrasting_area = cv2.threshold(straightened_area, 80, 255, cv2.THRESH_BINARY)[1]
        difference = 5
        for j in range(5):
            for i in range(5):
                x_min = 40 * i + difference
                x_max = 40 * (i + 1) - difference
                y_min = 40 * j + difference
                y_max = 40 * (j + 1) - difference
                zone = contrasting_area[y_min:y_max, x_min:x_max]

                if cv2.mean(zone)[0] > 127:
                    str_code += '0'
                else:
                    str_code += '1'
                cv2.rectangle(contrasting_area, (40 * i + difference, difference + 40 * j), (40 * (i + 1) - difference, 40 * (j + 1) - difference), (255, 255, 255))
        int_ret = int(str_code, 2)
        anchor = tops[0]
        if CATALOGUE.get(int_ret):
            rang_stud = CATALOGUE.get(int_ret)[0] - 1
            if rang_stud < len(group):
                text = 'done'
                cv2.putText(image_display, text, anchor, cv2.FONT_HERSHEY_SIMPLEX, 3.0, (0, 0, 255), 8)
    else:
        int_ret = 0
    return int_ret


def extract_identifiers(image, group=CLASS_TEST):
    """
    извлекает ВСЕ обнаруженные карточки на изображении и возвращает список
    считанных идентификаторов.
    """
    res = []
    contours, hierarchy, im_gray = get_contours_topology(image)

    for rang, contour in enumerate(contours):
        topology = hierarchy[0][rang]
        if topology[0] == -1 and topology[1] == -1 and topology[2] == -1 and topology[3] != -1:
            rang_fat = topology[3]
            topology_fat = hierarchy[0][rang_fat]
            rang_grand_fat = topology_fat[3]
            if rang_grand_fat != -1:
                grand_fat = contours[rang_grand_fat]
                rectangle = edging(grand_fat)
                if cv2.contourArea(grand_fat) > 0:
                    try:
                        res.append(extract_identifier(im_gray, rectangle, image, group))
                    except:
                        pass
    return res


def recognizes_cards(image, group=CLASS_TEST):
    if stop_scan:
        return []
    return [CATALOGUE.get(identifier) for identifier in extract_identifiers(image, group) if
            CATALOGUE.get(identifier)]


def delete_missing_students(group):
    """
     Принимает в качестве параметра список учащихся в классе.
     Предлагает пользователю отметить отсутствующих в окне Tkinter.
     Возвращает список фактически присутствующих учеников.
    """
    global remaining_students

    window = Tk.Tk()
    window.title('Отсутствующие')
    for student in group:
        presence = Tk.IntVar()
        presence.set(1)
        student.update({'present': presence})
        button = Tk.Checkbutton(window, text=student['name'] + ' ' + student['surname'], onvalue=0, offvalue=1, variable=student['present'], justify=Tk.RIGHT)
        button.pack(anchor="w")

    def confirm_input():
        window.quit()
        window.destroy()


    button = Tk.Button(window, text="Подтвердить", command=confirm_input)
    button.pack()
    window.mainloop()
    remaining_students = [rem for rem in group if rem['present'].get()]
    for student in remaining_students:
        student.pop('present')


def displaying_remaining_students():
    """Отображает список оставшихся учеников в окне Tkinter"""
    global remaining_students
    displaying_remaining_students = Tk.Tk()
    displaying_remaining_students.title('Нераспознанные ученики')
    card_remaining_stud = Tk.Frame(displaying_remaining_students)

    for student in remaining_students:
        label = Tk.Label(card_remaining_stud, text=student['name'] + ' ' + student['surname'])
        label.pack()
    card_remaining_stud.pack()

    def updating_list(window=displaying_remaining_students):
        global remaining_students
        if not remaining_students:
            return
        cadre = window.winfo_children()[0]
        if len(cadre.children) > len(remaining_students):
            print('#####')
            print(str(len(cadre.children)) + ',' + str(len(remaining_students)))
        cadre.destroy()
        cadre = Tk.Frame(window)
        for student in remaining_students:
            text = f"{student['name']} {student['surname']}"
            label = Tk.Label(cadre, text=text)
            label.pack()
        cadre.pack()
        window.after(500, updating_list)
    displaying_remaining_students.after(500, updating_list)
    displaying_remaining_students.mainloop()


def scan_video_stream(group, camera=0):
    """Сканирует видеопоток с камеры и распознает карточки,
        пока все ученики не будут распознаны"""
    global stop_scan
    stop_scan = False
    global remaining_students, answers
    answers = []
    cap = cv2.VideoCapture(camera, cv2.CAP_ANY)
    while remaining_students and not stop_scan:
        correct_reading, frame = cap.read()
        if correct_reading:
            cv2.imshow('catch', frame)
            for identification, answer in recognizes_cards(frame, group):
                if identification <= len(group) and group[identification - 1] in remaining_students:
                    answers.append((identification, answer))
                    rang_stud = remaining_students.index(group[identification - 1])
                    remaining_students.pop(rang_stud)
            cv2.imshow('catch', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            cap.release()
            cv2.destroyAllWindows()
        if not remaining_students:
            stop_scan = True
            cap.release()
            cv2.destroyAllWindows()
            print('Сканирование завершено')
            print('Результаты:')
            for identification, answer in answers:
                print(f'Студент: {group[identification - 1]["name"]} {group[identification - 1]["surname"]}, Ответ: {answer}')

    print(answers)


def real_time_scanner(group, camera=0, window=None):
    """Запускает сканирование видеопотока с камеры
        и отображает список оставшихся учеников в окне Tkinter"""
    if window:
        window.quit()
        window.destroy()
    delete_missing_students(group)
    t = threading.Thread(target=displaying_remaining_students)
    t.start()
    scan_video_stream(group, camera)


def main(camera=0):
    """запускает главное окно программы, которое позволяет
        выбрать класс и запустить сканирование"""
    main_window = Tk.Tk()
    main_window.title("Выбор класса")
    button_group_1 = Tk.Button(main_window, text="1 класс", command=(lambda: real_time_scanner(CLASS_TEST, camera, main_window)))

    button_group_1.pack()
    main_window.mainloop()


if __name__ == '__main__':
    main()
