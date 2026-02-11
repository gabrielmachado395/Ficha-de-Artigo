package com.gabri.fichadeartigo;

import com.getcapacitor.BridgeActivity;

import android.os.Bundle;

public class MainActivity extends BridgeActivity {
	@Override
	public void onCreate(Bundle savedInstanceState) {
		registerPlugin(RawTcpPrinterPlugin.class);
		super.onCreate(savedInstanceState);
	}
}
