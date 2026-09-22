import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'services/usb_stream_service.dart';
import 'services/discovery_service.dart';
import 'screens/display_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SecondScreenApp());
}

class SecondScreenApp extends StatelessWidget {
  const SecondScreenApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Second Screen',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorSchemeSeed: Colors.blueAccent,
        scaffoldBackgroundColor: const Color(0xFF121212),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _usbUrlController = TextEditingController(text: "ws://127.0.0.1:8080");
  final TextEditingController _wifiUrlController = TextEditingController(text: "ws://192.168.1.42:8080");
  final UsbStreamService _streamService = UsbStreamService();

  bool _isScanning = false;
  bool _isNavigating = false;
  List<DiscoveredServer> _discoveredServers = [];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _streamService.addListener(_handleServiceStateChange);
    _loadSavedSettings();
  }

  Future<void> _loadSavedSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final savedWifiUrl = prefs.getString('saved_wifi_url');
    if (savedWifiUrl != null && savedWifiUrl.isNotEmpty) {
      setState(() {
        _wifiUrlController.text = savedWifiUrl;
      });
    }
    // Auto scan for Wi-Fi servers on startup
    _scanWifiServers();
  }

  Future<void> _saveSettings(String wifiUrl) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('saved_wifi_url', wifiUrl);
  }

  void _handleServiceStateChange() {
    if (_streamService.status == ConnectionStateStatus.connected && !_isNavigating && mounted) {
      _isNavigating = true;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => DisplayScreen(streamService: _streamService),
        ),
      ).then((_) {
        _isNavigating = false;
      });
    }
  }

  Future<void> _scanWifiServers() async {
    if (_isScanning) return;
    setState(() {
      _isScanning = true;
    });

    final servers = await WifiDiscoveryService.scanServers();

    if (mounted) {
      setState(() {
        _isScanning = false;
        _discoveredServers = servers;
        if (servers.isNotEmpty) {
          _wifiUrlController.text = servers.first.wsUrl;
        }
      });
    }
  }

  void _connect(String url) {
    final trimmed = url.trim();
    if (trimmed.isNotEmpty) {
      if (_tabController.index == 1) {
        _saveSettings(trimmed);
      }
      _streamService.connect(trimmed);
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    _streamService.removeListener(_handleServiceStateChange);
    _streamService.dispose();
    _usbUrlController.dispose();
    _wifiUrlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Màn Hình Phụ PC', style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.blueAccent,
          indicatorWeight: 3,
          labelColor: Colors.blueAccent,
          unselectedLabelColor: Colors.white60,
          tabs: const [
            Tab(icon: Icon(Icons.usb), text: "Cáp USB (Siêu Mượt)"),
            Tab(icon: Icon(Icons.wifi), text: "Wi-Fi (Không Dây)"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildUsbTab(),
          _buildWifiTab(),
        ],
      ),
    );
  }

  // --- TAB 1: CÁP USB ---
  Widget _buildUsbTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.blueAccent.withAlpha(80),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Image.asset(
                  'assets/app_icon.png',
                  width: 96,
                  height: 96,
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Kết Nối Cáp USB Tốc Độ Cao',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 4),
          const Text(
            '60 FPS • Độ trễ cực thấp (< 15ms) • Băng thông tối đa',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.white60),
          ),
          const SizedBox(height: 24),

          _buildConnectionCard(
            controller: _usbUrlController,
            hintText: "ws://127.0.0.1:8080",
            icon: Icons.cable,
            onConnect: () => _connect(_usbUrlController.text),
          ),
          const SizedBox(height: 24),

          const Text(
            "Hướng dẫn kết nối USB:",
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
          ),
          const SizedBox(height: 10),
          _buildStepTile("1", "Cắm cáp USB & Bật 'Gỡ lỗi USB' (USB Debugging) trên điện thoại."),
          _buildStepTile("2", "Mở file 'start_usb_display.bat' trên máy tính."),
          _buildStepTile("3", "Nhấn nút 'KẾT NỐI MÀN HÌNH' ở trên."),
        ],
      ),
    );
  }

  // --- TAB 2: MẠNG WI-FI ---
  Widget _buildWifiTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.greenAccent.withAlpha(80),
                    blurRadius: 16,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Image.asset(
                  'assets/app_icon.png',
                  width: 96,
                  height: 96,
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'Kết Nối Mạng Wi-Fi Không Dây',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 4),
          const Text(
            'Tiện lợi • Không cần dây cáp • Tự do di chuyển',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: Colors.white60),
          ),
          const SizedBox(height: 24),

          // Auto scan button
          OutlinedButton.icon(
            onPressed: _isScanning ? null : _scanWifiServers,
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.greenAccent,
              side: const BorderSide(color: Colors.greenAccent),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            icon: _isScanning
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.greenAccent),
                  )
                : const Icon(Icons.radar),
            label: Text(_isScanning ? "Đang quét mạng Wi-Fi..." : "Tự động dò tìm máy tính"),
          ),
          const SizedBox(height: 14),

          // Discovered servers list
          if (_discoveredServers.isNotEmpty) ...[
            const Text(
              "Máy tính tìm thấy trong Wi-Fi:",
              style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            ..._discoveredServers.map((server) {
              return Card(
                color: const Color(0xFF1E281E),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: const BorderSide(color: Colors.greenAccent, width: 0.8),
                ),
                child: ListTile(
                  leading: const Icon(Icons.computer, color: Colors.greenAccent),
                  title: Text(server.hostname, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                  subtitle: Text(server.wsUrl, style: const TextStyle(color: Colors.white60, fontSize: 12)),
                  trailing: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.greenAccent.shade700,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    ),
                    onPressed: () {
                      _wifiUrlController.text = server.wsUrl;
                      _connect(server.wsUrl);
                    },
                    child: const Text("Kết nối"),
                  ),
                ),
              );
            }),
            const SizedBox(height: 16),
          ],

          _buildConnectionCard(
            controller: _wifiUrlController,
            hintText: "ws://192.168.1.42:8080",
            icon: Icons.wifi,
            onConnect: () => _connect(_wifiUrlController.text),
          ),
          const SizedBox(height: 24),

          const Text(
            "Hướng dẫn kết nối Wi-Fi:",
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
          ),
          const SizedBox(height: 10),
          _buildStepTile("1", "Kết nối điện thoại và máy tính vào CÙNG một mạng Wi-Fi."),
          _buildStepTile("2", "Trên máy tính, mở file 'start_wifi_display.bat'."),
          _buildStepTile("3", "Bấm 'Tự động dò tìm máy tính' hoặc nhập IP hiển thị trên màn hình máy tính."),
        ],
      ),
    );
  }

  Widget _buildConnectionCard({
    required TextEditingController controller,
    required String hintText,
    required IconData icon,
    required VoidCallback onConnect,
  }) {
    return Card(
      color: const Color(0xFF1E1E1E),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Địa chỉ máy chủ (WebSocket URL):",
              style: TextStyle(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
              decoration: InputDecoration(
                hintText: hintText,
                hintStyle: const TextStyle(color: Colors.white30),
                prefixIcon: Icon(icon, color: Colors.blueAccent),
                filled: true,
                fillColor: const Color(0xFF2C2C2C),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              ),
            ),
            const SizedBox(height: 16),

            ListenableBuilder(
              listenable: _streamService,
              builder: (context, _) {
                final isConnecting = _streamService.status == ConnectionStateStatus.connecting;
                return ElevatedButton(
                  onPressed: isConnecting ? null : onConnect,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueAccent,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(double.infinity, 50),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    elevation: 4,
                  ),
                  child: isConnecting
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
                        )
                      : const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.play_arrow_rounded, size: 26),
                            SizedBox(width: 8),
                            Text('KẾT NỐI MÀN HÌNH', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                          ],
                        ),
                );
              },
            ),

            ListenableBuilder(
              listenable: _streamService,
              builder: (context, _) {
                if (_streamService.status == ConnectionStateStatus.error) {
                  return Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline, color: Colors.redAccent, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "Không thể kết nối. Kiểm tra Server máy tính và tường lửa (Firewall)!",
                            style: const TextStyle(color: Colors.redAccent, fontSize: 12),
                          ),
                        ),
                      ],
                    ),
                  );
                }
                return const SizedBox.shrink();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStepTile(String step, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 26,
            height: 26,
            decoration: BoxDecoration(
              color: Colors.white12,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white24),
            ),
            alignment: Alignment.center,
            child: Text(step, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.3)),
          ),
        ],
      ),
    );
  }
}
