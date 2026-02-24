package com.example.myapp

import android.graphics.Bitmap
import android.os.Bundle
import android.view.PixelCopy
import android.view.View
import android.view.Window
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp


/**
 * Example Activity demonstrating ReusablePopup usage.
 *
 * This shows:
 *  1. Loading popup config from JSON
 *  2. Capturing a background screenshot for the glass blur
 *  3. Showing/dismissing the popup
 *  4. Handling button callbacks
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TVAppScreen()
        }
    }
}

@Composable
private fun TVAppScreen() {
    val view = LocalView.current

    // State: is popup visible?
    var showPopup by remember { mutableStateOf(false) }

    // State: captured background bitmap for glass blur
    var backgroundBitmap by remember { mutableStateOf<Bitmap?>(null) }

    // =================================================================
    // Your actual TV app content goes here
    // This is just a placeholder example
    // =================================================================
    Box(modifier = Modifier.fillMaxSize()) {
        // Background — replace with your actual TV app screen
        Image(
            painter = painterResource(id = R.drawable.tv_background),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize()
        )

        // Example: A button that triggers the popup
        Button(
            onClick = {
                // Capture current screen as bitmap before showing popup
                captureScreenshot(view) { bitmap ->
                    backgroundBitmap = bitmap
                    showPopup = true
                }
            },
            modifier = Modifier
                .align(Alignment.Center)
                .padding(32.dp)
        ) {
            Text(
                text = "Show Popup",
                fontSize = 20.sp
            )
        }
    }

    // =================================================================
    // Popup — shown when showPopup = true
    // =================================================================
    if (showPopup) {
        ReusablePopup(
            backgroundBitmap = backgroundBitmap,
            onButtonClick = { action ->
                when (action) {
                    "open_setting" -> {
                        showPopup = false
                    }
                    "dismiss" -> {
                        showPopup = false
                    }
                    else -> {
                        showPopup = false
                    }
                }
            },
            onDismiss = {
                showPopup = false
            }
        )
    }
}

// =============================================================================
// SCREENSHOT CAPTURE — For the frosted glass background blur
// =============================================================================

/**
 * Captures the current screen content as a Bitmap.
 *
 * Uses PixelCopy (API 26+) for accurate capture including
 * hardware-accelerated content. Falls back to View.drawingCache
 * on older devices.
 *
 * The captured bitmap is passed to ReusablePopup as backgroundBitmap
 * to create the frosted glass blur effect.
 */
private fun captureScreenshot(view: View, onCaptured: (Bitmap?) -> Unit) {
    try {
        val window: Window = (view.context as? ComponentActivity)?.window
            ?: run { onCaptured(null); return }

        val bitmap = Bitmap.createBitmap(
            view.width,
            view.height,
            Bitmap.Config.ARGB_8888
        )

        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            // API 26+: Use PixelCopy for accurate capture
            PixelCopy.request(
                window,
                bitmap,
                { result ->
                    if (result == PixelCopy.SUCCESS) {
                        onCaptured(bitmap)
                    } else {
                        onCaptured(null)
                    }
                },
                android.os.Handler(android.os.Looper.getMainLooper())
            )
        } else {
            // Fallback: Draw view to canvas
            @Suppress("DEPRECATION")
            view.isDrawingCacheEnabled = true
            @Suppress("DEPRECATION")
            val cache = view.drawingCache
            if (cache != null) {
                onCaptured(cache.copy(Bitmap.Config.ARGB_8888, false))
            } else {
                onCaptured(null)
            }
            @Suppress("DEPRECATION")
            view.isDrawingCacheEnabled = false
        }
    } catch (e: Exception) {
        e.printStackTrace()
        onCaptured(null)
    }
}

