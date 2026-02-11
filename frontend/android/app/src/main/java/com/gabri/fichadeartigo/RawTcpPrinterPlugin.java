package com.gabri.fichadeartigo;

import android.util.Base64;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;

@CapacitorPlugin(name = "RawTcpPrinter")
public class RawTcpPrinterPlugin extends Plugin {

    @PluginMethod
    public void probe(PluginCall call) {
        final String host = call.getString("host", "");
        final int port = call.getInt("port", 9100);
        final int timeoutMs = call.getInt("timeoutMs", 5000);

        if (host == null || host.trim().isEmpty()) {
            call.reject("host é obrigatório");
            return;
        }
        if (port <= 0 || port > 65535) {
            call.reject("port inválido");
            return;
        }

        try {
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(host, port), timeoutMs);
            socket.setSoTimeout(timeoutMs);
            socket.close();

            JSObject ret = new JSObject();
            ret.put("ok", true);
            call.resolve(ret);
        } catch (Exception ex) {
            call.reject("Falha ao conectar na impressora (TCP)", ex);
        }
    }

    @PluginMethod
    public void send(PluginCall call) {
        final String host = call.getString("host", "");
        final int port = call.getInt("port", 9100);
        final String dataBase64 = call.getString("dataBase64", "");
        final int timeoutMs = call.getInt("timeoutMs", 5000);

        if (host == null || host.trim().isEmpty()) {
            call.reject("host é obrigatório");
            return;
        }
        if (dataBase64 == null || dataBase64.trim().isEmpty()) {
            call.reject("dataBase64 é obrigatório");
            return;
        }
        if (port <= 0 || port > 65535) {
            call.reject("port inválido");
            return;
        }

        byte[] bytes;
        try {
            bytes = Base64.decode(dataBase64, Base64.DEFAULT);
        } catch (Exception ex) {
            call.reject("dataBase64 inválido", ex);
            return;
        }

        try {
            Socket socket = new Socket();
            socket.connect(new InetSocketAddress(host, port), timeoutMs);
            socket.setSoTimeout(timeoutMs);

            OutputStream os = socket.getOutputStream();
            os.write(bytes);
            os.flush();
            os.close();

            socket.close();

            JSObject ret = new JSObject();
            ret.put("ok", true);
            call.resolve(ret);
        } catch (Exception ex) {
            call.reject("Falha ao enviar para a impressora (TCP)", ex);
        }
    }
}
