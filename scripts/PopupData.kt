package com.example.myapp

import android.content.Context
import org.json.JSONObject

// =============================================================================
// Data Models
// =============================================================================

/**
 * Represents a single image card in the popup content section.
 *
 * @param drawable  Name of the drawable resource (without extension).
 *                  Resolved at runtime via resources.getIdentifier().
 * @param label     Text shown above the image card (e.g. "OFF", "ON").
 * @param enhanced  If true: vivid saturated look + cyan glow border.
 *                  If false: desaturated muted look.
 */
data class PopupImageItem(
    val drawable: String,
    val label: String,
    val enhanced: Boolean
)

/**
 * Represents a button in the popup footer.
 *
 * @param text    Display text on the button.
 * @param action  Action identifier string returned via onButtonClick callback.
 */
data class PopupButtonItem(
    val text: String,
    val action: String
)

/**
 * Complete popup configuration parsed from JSON.
 *
 * @param title    Optional title shown above the message. Null = hidden.
 * @param message  Body text always shown below the title (or at the top if no title).
 * @param images   List of image cards. ≤2 = centered row, >2 = scrollable carousel.
 * @param buttons  List of action buttons shown at the bottom.
 */
data class PopupData(
    val title: String?,
    val message: String,
    val images: List<PopupImageItem>,
    val buttons: List<PopupButtonItem>
)

// =============================================================================
// JSON Parser — uses org.json (built-in, no external dependency)
// =============================================================================

object PopupDataParser {

    private const val DefaultAssetFile = "popup_config.json"

    /**
     * Parse popup config from a JSON file in the assets folder.
     *
     * Usage:
     *   val data = PopupDataParser.fromAsset(context, "popup_config.json")
     */
    fun fromAsset(context: Context, fileName: String = DefaultAssetFile): PopupData {
        val jsonString = context.assets
            .open(fileName)
            .bufferedReader()
            .use { it.readText() }
        return fromJsonString(jsonString)
    }

    /**
     * Parse popup config from a raw JSON string.
     * Useful for testing or when JSON comes from network/other sources.
     */
    fun fromJsonString(jsonString: String): PopupData {
        val json = JSONObject(jsonString)

        val rawTitle = json.optString("title", "")
        val title = rawTitle.takeIf { it.isNotBlank() && !it.equals("null", ignoreCase = true) }

        // Message is required
        val message = json.getString("message")

        // Parse images array
        val imagesArray = json.getJSONArray("images")
        val images = (0 until imagesArray.length()).map { i ->
            val imgObj = imagesArray.getJSONObject(i)
            PopupImageItem(
                drawable = imgObj.getString("drawable"),
                label = imgObj.getString("label"),
                enhanced = imgObj.getBoolean("enhanced")
            )
        }

        // Parse buttons array
        val buttonsArray = json.getJSONArray("buttons")
        val buttons = (0 until buttonsArray.length()).map { i ->
            val btnObj = buttonsArray.getJSONObject(i)
            PopupButtonItem(
                text = btnObj.getString("text"),
                action = btnObj.getString("action")
            )
        }

        return PopupData(
            title = title,
            message = message,
            images = images,
            buttons = buttons
        )
    }
}
