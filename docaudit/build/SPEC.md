# Quy cách biên soạn — bản 2.0 (bắt buộc tuân thủ)

## 1. Định dạng nguồn (markup dòng)

Mỗi dòng bắt đầu bằng một thẻ, cách nội dung bằng đúng một dấu cách.

```
H1 CHƯƠNG 1. TỔNG QUAN ...
H2 1.1. Định nghĩa ...
H3 1.1.1. Tiến trình lịch sử ...
H4 1.1.1.1. Định nghĩa dựa trên thời gian ...
P  <đoạn văn>
BUL <mục gạch đầu dòng — dùng hạn chế>
TABLE <nội dung caption, kết thúc bằng [số tài liệu] rồi dấu chấm>
COLW 1.2,1.0,1.0        # tỷ lệ bề rộng cột, sẽ được chuẩn hoá về 15,5 cm
ALIGN l,c,j             # l=trái, c=giữa, j=đều hai bên (mặc định: cột 1 trái, còn lại giữa)
FSIZE 11                # cỡ chữ trong bảng, mặc định 11,5
H  <ô tiêu đề>|<ô tiêu đề>|<ô tiêu đề>
R  <ô>|<ô>|<ô>
ENDTABLE
FIG imageN.jpg | <bề rộng cm> | <caption, kết thúc bằng [số tài liệu] rồi dấu chấm>
```

Ký hiệu nội dòng: `**đậm**`, `*nghiêng*`, `^{số mũ}`, `_{chỉ số dưới}`.
Ví dụ bắt buộc: `CHA_{2}DS_{2}-VASc`, `kg/m^{2}`, `µV·ms`.

## 2. Quy tắc caption (áp dụng đồng nhất cho **mọi** bảng và hình)

- Bảng: caption **trên** bảng. Hình: caption **dưới** hình. Cùng một kiểu chữ.
- Cấu trúc: `Bảng <chương>.<số>. <Nội dung> [<tài liệu>].`
- Trích dẫn đặt **ngay sau nội dung caption**, trước dấu chấm cuối.
- **Tuyệt đối không** viết "Nguồn:", "Theo:", "Trích từ:" ở bất kỳ đâu.
- **Mọi** caption phải kết thúc bằng `[...]` rồi dấu chấm. Không có ngoại lệ.
- Caption là **mô tả ngắn**, tối đa **35 từ**. Mọi diễn giải chi tiết chuyển vào thân bài.
- Mỗi bảng và mỗi hình phải được **gọi tên ít nhất một lần** trong thân bài, ở đúng
  đoạn văn mà nó minh hoạ, dạng `(Bảng 2.4)` hoặc `(Hình 3.2)`.
- Nhiều tham chiếu gộp vào **một** cặp ngoặc: `(Bảng 3.2 và Bảng 3.3)`, không viết
  `(Bảng 3.2) (Bảng 3.3)`.

## 3. Quy tắc bảng

- Tối đa **6 cột**. Bảng 7 cột phải được tách hoặc chuyển cột thành hàng.
- Không có cột nào được để trống hoặc ghi "Không áp dụng" ở quá một phần ba số hàng.
- Một bảng chỉ chứa **một loại đối tượng**. Không trộn "cấu phần thang điểm" với
  "phân tầng nguy cơ" trong cùng một bảng — tách thành hai bảng.
- Bảng so sánh thử nghiệm phải có cột **nhóm chứng** để các con số so sánh được.
- Ô dữ liệu viết ngắn; câu dài chuyển vào thân bài.
- Đơn vị và cách viết liều **thống nhất toàn văn**: "90 mg hai lần mỗi ngày"
  (không dùng "90 mg × 2"); nồng độ luôn ghi kép "mg/dL (mmol/L)".

## 4. Quy tắc trích dẫn

- Chỉ dùng số tài liệu có trong `REFERENCES.md`. **Không được bịa số**.
- Trích dẫn phải **thực sự chống đỡ** câu văn. Nếu không chắc, đổi câu văn chứ
  không đổi số trích dẫn.
- Khoảng liên tiếp viết `[14-17]`; rời rạc viết `[5,18,53]`; hỗn hợp `[5,14-17,53]`.
- Trích dẫn đặt cuối câu, trước dấu chấm.

## 5. Quy tắc ngôn ngữ

- Dấu gạch nối khoảng giá trị: dùng **en dash** `–` (5–7%, 18–60 tuổi), không dùng
  "từ … đến …" xen kẽ.
- Dấu thập phân dùng **dấu phẩy** (8,2%; 0,68), dấu nghìn dùng **dấu chấm** (5.170).
- Thuật ngữ tiếng Việt phải **nhất quán tuyệt đối** trong toàn chuyên đề:
  - *cơn thiếu máu não thoáng qua* (viết tắt TIA sau lần đầu)
  - *đột quỵ thiếu máu não nhẹ* (không dùng "đột quỵ nhẹ" đơn lẻ ở văn viết trang trọng)
  - *cộng hưởng từ khuếch tán*, *chuỗi xung khuếch tán*
  - *kháng kết tập tiểu cầu kép*, *thuốc kháng đông đường uống trực tiếp*
  - *đột quỵ lấp mạch chưa rõ nguồn* (ESUS)
  - *lỗ bầu dục thông* (PFO)
  - *tỷ số nguy cơ* (HR), *tỷ số chênh* (OR), *khoảng tin cậy 95%* (KTC 95%)
  - *bóc nội mạc động mạch cảnh*, *đặt stent động mạch cảnh*
- Mỗi chữ viết tắt phải được **định nghĩa ở lần dùng đầu tiên** trong thân bài và
  phải có trong DANH MỤC CHỮ VIẾT TẮT.
- Không mở một mục bằng "Tóm lại".

## 6. Quy tắc nội dung

- Bám tuyệt đối `CORRECTIONS.md`. Mọi giá trị đã bị đánh dấu SAI **không được xuất hiện**.
- Một sự kiện, một thử nghiệm, một con số chỉ được **trình bày đầy đủ một lần**, tại
  mục được chỉ định là mục chính. Các nơi khác chỉ nhắc bằng một mệnh đề kèm tham
  chiếu chéo `(xem Mục 1.5.2)`.
- Không đưa nội dung điều trị vào Chương 2 (chẩn đoán) và ngược lại; chỉ tham chiếu chéo.
- Mỗi mục cấp 3 phải có **ít nhất hai đoạn văn**; mục nào chỉ có một đoạn thì gộp
  vào mục lân cận hoặc mở rộng.
- Mỗi đoạn văn 90–180 từ. Không viết đoạn một câu.
- Khi nêu kết quả thử nghiệm: nêu **tên thử nghiệm, cỡ mẫu, quần thể, can thiệp,
  kết cục chính với con số cả hai nhánh, ước lượng hiệu quả kèm KTC 95%, và biến
  cố an toàn**. Nêu rõ kết cục chính là gì (đột quỵ mọi loại, hay riêng nhồi máu não,
  hay kết cục gộp) — đây là lỗi phổ biến nhất của bản cũ.
