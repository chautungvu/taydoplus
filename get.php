<?php
// 1. Danh sách các tài khoản hợp lệ (Bạn có thể thêm bao nhiêu tùy ý)
$valid_users = [
    "admin"     => "koaibietca",
    "vuthituyenTHA001"   => "123",
    "tha_vl01my" => "1",
    "hn_01_tdplus"  => "123"
];

// 2. Đường dẫn đến file M3U gốc
$m3u_url = "https://tinyurl.com/tdpvip";

// 3. Lấy dữ liệu từ URL
$user = isset($_GET['username']) ? $_GET['username'] : '';
$pass = isset($_GET['password']) ? $_GET['password'] : '';

// 4. Kiểm tra tài khoản
// array_key_exists kiểm tra xem username có trong danh sách không
// Sau đó so sánh mật khẩu tương ứng
if (array_key_exists($user, $valid_users) && $valid_users[$user] === $pass) {
    // Đúng tài khoản và mật khẩu -> Chuyển hướng
    header("Location: " . $m3u_url);
    exit;
} else {
    // Sai tài khoản hoặc mật khẩu -> Từ chối
    http_response_code(403);
    echo "Đéo phải ạ. Tìm password và user khác ạ.";
    exit;
}
?>
