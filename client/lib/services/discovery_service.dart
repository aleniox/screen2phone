import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';

class DiscoveredServer {
  final String hostname;
  final String ip;
  final int port;
  final String wsUrl;

  DiscoveredServer({
    required this.hostname,
    required this.ip,
    required this.port,
    required this.wsUrl,
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DiscoveredServer &&
          runtimeType == other.runtimeType &&
          wsUrl == other.wsUrl;

  @override
  int get hashCode => wsUrl.hashCode;
}

class WifiDiscoveryService {
  static const int discoveryPort = 8088;
  static const String magicRequest = "DISCOVER_SECOND_SCREEN";

  static Future<List<DiscoveredServer>> scanServers({Duration timeout = const Duration(seconds: 3)}) async {
    final List<DiscoveredServer> servers = [];
    RawDatagramSocket? socket;
    Timer? timer;

    try {
      socket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      socket.broadcastEnabled = true;

      final data = utf8.encode(magicRequest);
      // Broadcast to local subnet
      socket.send(data, InternetAddress("255.255.255.255"), discoveryPort);

      final completer = Completer<List<DiscoveredServer>>();
      timer = Timer(timeout, () {
        if (!completer.isCompleted) {
          completer.complete(servers);
        }
      });

      socket.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          final datagram = socket?.receive();
          if (datagram != null) {
            try {
              final text = utf8.decode(datagram.data);
              final jsonMap = json.decode(text);
              if (jsonMap is Map<String, dynamic> && jsonMap["service"] == "second_screen_server") {
                final server = DiscoveredServer(
                  hostname: jsonMap["hostname"] ?? "Windows PC",
                  ip: jsonMap["ip"] ?? datagram.address.address,
                  port: jsonMap["port"] ?? 8080,
                  wsUrl: jsonMap["ws_url"] ?? "ws://${datagram.address.address}:${jsonMap["port"] ?? 8080}",
                );
                if (!servers.contains(server)) {
                  servers.add(server);
                }
              }
            } catch (e) {
              debugPrint("Error parsing discovery datagram: $e");
            }
          }
        }
      });

      return await completer.future;
    } catch (e) {
      debugPrint("Wi-Fi discovery error: $e");
      return servers;
    } finally {
      timer?.cancel();
      socket?.close();
    }
  }
}
