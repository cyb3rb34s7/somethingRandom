package com.example.myapp

import android.graphics.Bitmap
import android.graphics.BlurMaskFilter
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.RenderEffect
import android.graphics.Shader
import android.os.Build
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusProperties
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onKeyEvent
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import kotlin.math.roundToInt

private object PopupColors {
    val Scrim = Color(4, 10, 20).copy(alpha = 0.10f)
    val GlassTint = Color(8, 18, 28).copy(alpha = 0.18f)
    val ModalBorder = Color.White.copy(alpha = 0.08f)
    val ContentBg = Color(0xFF0A0E14)
    val CyanAccent = Color(0xFF29D2E4)
    val OffLabel = Color.White.copy(alpha = 0.55f)
    val OffCardBorder = Color.White.copy(alpha = 0.06f)
    val OnCardBorder = CyanAccent.copy(alpha = 0.5f)
    val MessageText = Color.White.copy(alpha = 0.92f)
    val TitleText = Color.White
    val ButtonFocusedBg = Color(0xFFF0F0F0)
    val ButtonFocusedText = Color(0xFF0E1218)
    val ButtonUnfocusedBg = Color(0xFF111318)
    val ButtonUnfocusedText = Color.White.copy(alpha = 0.88f)
}

private data class UiScale(val density: Density, val factor: Float) {
    fun dp(px: Float): Dp = with(density) { (px * factor).toDp() }
    fun sp(px: Float): TextUnit = with(density) { (px * factor).toSp() }
    fun px(px: Float): Float = px * factor
}

private val OffColorMatrix = ColorMatrix().apply {
    setToSaturation(0.15f)
    val scale = 0.72f * 0.8f
    val offset = (1f - 0.8f) * 128f * 0.72f
    timesAssign(
        ColorMatrix(
            floatArrayOf(
                scale, 0f, 0f, 0f, offset,
                0f, scale, 0f, 0f, offset,
                0f, 0f, scale, 0f, offset,
                0f, 0f, 0f, 1f, 0f
            )
        )
    )
}

private val OnColorMatrix = ColorMatrix().apply {
    setToSaturation(1.45f)
    val scale = 1.14f * 1.1f
    val offset = (1f - 1.1f) * 128f * 1.14f
    timesAssign(
        ColorMatrix(
            floatArrayOf(
                scale, 0f, 0f, 0f, offset,
                0f, scale, 0f, 0f, offset,
                0f, 0f, scale, 0f, offset,
                0f, 0f, 0f, 1f, 0f
            )
        )
    )
}

@Composable
fun ReusablePopup(
    backgroundBitmap: Bitmap? = null,
    onButtonClick: (action: String) -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val popupData = remember { PopupDataParser.fromAsset(context) }

    val density = LocalDensity.current
    val screenWidthDp = LocalConfiguration.current.screenWidthDp.dp
    val widthPx = with(density) { screenWidthDp.toPx() }
    val scale = UiScale(density, if (widthPx > 0f) widthPx / 1920f else 1f)
    val modalShape = RoundedCornerShape(scale.dp(28f))
    val maxModalWidth = scale.dp(1150f)
    val modalWidth = if (screenWidthDp * 0.6f < maxModalWidth) screenWidthDp * 0.6f else maxModalWidth
    val textShadow = Shadow(
        color = Color.Black.copy(alpha = 0.25f),
        offset = Offset(0f, scale.px(1f)),
        blurRadius = scale.px(3f)
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(PopupColors.Scrim)
            .onPreviewKeyEvent { event ->
                if (event.type == KeyEventType.KeyDown && event.key == Key.Back) {
                    onDismiss()
                    true
                } else {
                    false
                }
            },
        contentAlignment = Alignment.Center
    ) {

        val imageFocusRequesters = remember(popupData.images.size) {
            List(popupData.images.size) { FocusRequester() }
        }
        val buttonFocusRequesters = remember(popupData.buttons.size) {
            List(popupData.buttons.size) { FocusRequester() }
        }

        Box(
            modifier = Modifier
                .width(modalWidth)
                .wrapContentHeight()
                .shadow(
                    elevation = scale.dp(24f),
                    shape = modalShape,
                    clip = false,
                    ambientColor = Color.Black.copy(alpha = 0.3f),
                    spotColor = Color.Black.copy(alpha = 0.3f)
                )
                .shadow(
                    elevation = scale.dp(8f),
                    shape = modalShape,
                    clip = false,
                    ambientColor = Color.Black.copy(alpha = 0.15f),
                    spotColor = Color.Black.copy(alpha = 0.15f)
                )
                .clip(modalShape)
        ) {
            if (backgroundBitmap != null) {
                BlurredBackground(
                    bitmap = backgroundBitmap,
                    blurRadiusPx = scale.px(42f),
                    modifier = Modifier.matchParentSize()
                )
            } else {
                Box(
                    modifier = Modifier
                        .matchParentSize()
                        .background(Color(8, 18, 28).copy(alpha = 0.65f))
                )
            }

            Box(
                modifier = Modifier
                    .matchParentSize()
                    .background(PopupColors.GlassTint)
            )

            Box(
                modifier = Modifier
                    .matchParentSize()
                    .border(scale.dp(1f), PopupColors.ModalBorder, modalShape)
            )

            Box(
                modifier = Modifier
                    .matchParentSize()
                    .drawBehind {
                        val stroke = scale.px(1f)
                        drawLine(
                            color = Color.White.copy(alpha = 0.06f),
                            start = Offset(0f, stroke / 2f),
                            end = Offset(size.width, stroke / 2f),
                            strokeWidth = stroke
                        )
                        drawLine(
                            color = Color.White.copy(alpha = 0.02f),
                            start = Offset(0f, size.height - stroke / 2f),
                            end = Offset(size.width, size.height - stroke / 2f),
                            strokeWidth = stroke
                        )
                    }
            )

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .wrapContentHeight()
            ) {
                if (popupData.title != null) {
                    Text(
                        text = popupData.title,
                        color = PopupColors.TitleText,
                        fontSize = scale.sp(36f),
                        fontWeight = FontWeight.Bold,
                        lineHeight = scale.sp(46.8f),
                        style = TextStyle(shadow = textShadow),
                        modifier = Modifier.padding(
                            start = scale.dp(48f),
                            end = scale.dp(48f),
                            top = scale.dp(44f)
                        )
                    )
                    MessageText(
                        text = popupData.message,
                        topPadding = scale.dp(12f),
                        scale = scale,
                        textShadow = textShadow
                    )
                } else {
                    MessageText(
                        text = popupData.message,
                        topPadding = scale.dp(44f),
                        scale = scale,
                        textShadow = textShadow
                    )
                }

                ContentSection(
                    images = popupData.images,
                    scale = scale,
                    imageFocusRequesters = imageFocusRequesters,
                    downTarget = buttonFocusRequesters.firstOrNull()
                )

                ButtonRow(
                    buttons = popupData.buttons,
                    scale = scale,
                    buttonFocusRequesters = buttonFocusRequesters,
                    upTarget = imageFocusRequesters.firstOrNull(),
                    onButtonClick = onButtonClick
                )
            }
        }
    }
}

@Composable
private fun MessageText(
    text: String,
    topPadding: Dp,
    scale: UiScale,
    textShadow: Shadow
) {
    Text(
        text = text,
        color = PopupColors.MessageText,
        fontSize = scale.sp(30f),
        fontWeight = FontWeight.Normal,
        lineHeight = scale.sp(45f),
        letterSpacing = scale.sp(0.3f),
        style = TextStyle(shadow = textShadow),
        modifier = Modifier.padding(
            start = scale.dp(48f),
            end = scale.dp(48f),
            top = topPadding,
            bottom = scale.dp(32f)
        )
    )
}

@Composable
private fun ContentSection(
    images: List<PopupImageItem>,
    scale: UiScale,
    imageFocusRequesters: List<FocusRequester>,
    downTarget: FocusRequester?
) {
    val sectionShape = RoundedCornerShape(scale.dp(20f))

    Box(
        modifier = Modifier
            .padding(horizontal = scale.dp(36f))
            .fillMaxWidth()
            .wrapContentHeight()
            .clip(sectionShape)
            .drawBehind {
                drawRect(color = PopupColors.ContentBg)
                val minSize = size.minDimension

                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(20, 120, 140).copy(alpha = 0.12f),
                            Color.Transparent
                        ),
                        center = Offset(size.width * 0.65f, size.height * 0.45f),
                        radius = minSize * 0.55f
                    ),
                    radius = minSize * 0.55f,
                    center = Offset(size.width * 0.65f, size.height * 0.45f)
                )

                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(40, 60, 130).copy(alpha = 0.08f),
                            Color.Transparent
                        ),
                        center = Offset(size.width * 0.25f, size.height * 0.7f),
                        radius = minSize * 0.5f
                    ),
                    radius = minSize * 0.5f,
                    center = Offset(size.width * 0.25f, size.height * 0.7f)
                )

                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(30, 80, 100).copy(alpha = 0.06f),
                            Color.Transparent
                        ),
                        center = Offset(size.width * 0.45f, size.height * 0.15f),
                        radius = minSize * 0.45f
                    ),
                    radius = minSize * 0.45f,
                    center = Offset(size.width * 0.45f, size.height * 0.15f)
                )

                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(
                            Color(15, 50, 65).copy(alpha = 0.08f),
                            Color.Transparent
                        ),
                        center = Offset(size.width * 0.5f, size.height * 0.5f),
                        radius = minSize * 0.7f
                    ),
                    radius = minSize * 0.7f,
                    center = Offset(size.width * 0.5f, size.height * 0.5f)
                )
            }
            .padding(
                vertical = scale.dp(32f),
                horizontal = scale.dp(48f)
            ),
        contentAlignment = Alignment.Center
    ) {
        if (images.size <= 2) {
            ImageCardRow(
                images = images,
                scale = scale,
                imageFocusRequesters = imageFocusRequesters,
                downTarget = downTarget
            )
        } else {
            ImageCardCarousel(
                images = images,
                scale = scale,
                imageFocusRequesters = imageFocusRequesters,
                downTarget = downTarget
            )
        }
    }
}

@Composable
private fun ImageCardRow(
    images: List<PopupImageItem>,
    scale: UiScale,
    imageFocusRequesters: List<FocusRequester>,
    downTarget: FocusRequester?
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(scale.dp(28f)),
        verticalAlignment = Alignment.Top,
        modifier = Modifier
            .wrapContentWidth()
            .wrapContentHeight()
    ) {
        images.forEachIndexed { index, item ->
            ImageCard(
                item = item,
                scale = scale,
                modifier = Modifier
                    .requiredWidth(scale.dp(240f))
                    .focusRequester(imageFocusRequesters[index])
                    .focusable()
                    .focusProperties {
                        if (index > 0) left = imageFocusRequesters[index - 1]
                        if (index < imageFocusRequesters.lastIndex) right = imageFocusRequesters[index + 1]
                        if (downTarget != null) down = downTarget
                    }
            )
        }
    }
}

@Composable
private fun ImageCardCarousel(
    images: List<PopupImageItem>,
    scale: UiScale,
    imageFocusRequesters: List<FocusRequester>,
    downTarget: FocusRequester?
) {
    val listState = rememberLazyListState()
    var focusedIndex by remember { mutableIntStateOf(0) }

    LaunchedEffect(focusedIndex) {
        if (focusedIndex in images.indices) {
            listState.animateScrollToItem(focusedIndex)
        }
    }

    LazyRow(
        state = listState,
        horizontalArrangement = Arrangement.spacedBy(scale.dp(28f)),
        contentPadding = PaddingValues(horizontal = scale.dp(8f)),
        modifier = Modifier
            .fillMaxWidth()
            .wrapContentHeight()
    ) {
        itemsIndexed(images) { index, item ->
            ImageCard(
                item = item,
                scale = scale,
                modifier = Modifier
                    .requiredWidth(scale.dp(240f))
                    .focusRequester(imageFocusRequesters[index])
                    .onFocusChanged { state ->
                        if (state.isFocused) focusedIndex = index
                    }
                    .focusable()
                    .focusProperties {
                        if (index > 0) left = imageFocusRequesters[index - 1]
                        if (index < imageFocusRequesters.lastIndex) right = imageFocusRequesters[index + 1]
                        if (downTarget != null) down = downTarget
                    }
            )
        }
    }
}

@Composable
private fun ImageCard(
    item: PopupImageItem,
    scale: UiScale,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val resId = remember(item.drawable) {
        context.resources.getIdentifier(
            item.drawable,
            "drawable",
            context.packageName
        )
    }

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(scale.dp(12f)),
        modifier = modifier.wrapContentHeight()
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(scale.dp(5f))
        ) {
            Text(
                text = item.label.uppercase(),
                color = if (item.enhanced) PopupColors.CyanAccent else PopupColors.OffLabel,
                fontSize = scale.sp(22f),
                fontWeight = FontWeight.Bold,
                letterSpacing = scale.sp(2.2f)
            )
            if (item.enhanced) {
                Text(
                    text = "✦",
                    color = PopupColors.CyanAccent,
                    fontSize = scale.sp(18f)
                )
            }
        }

        val cornerRadius = scale.dp(14f)
        val cornerRadiusPx = scale.px(14f)
        val borderWidth = if (item.enhanced) scale.dp(2.5f) else scale.dp(2f)
        val borderWidthPx = if (item.enhanced) scale.px(2.5f) else scale.px(2f)

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(16f / 11f)
                .then(
                    if (item.enhanced) {
                        Modifier.drawBehind {
                            drawGlowRoundRect(
                                color = PopupColors.CyanAccent.copy(alpha = 0.18f),
                                blurRadiusPx = scale.px(12f),
                                cornerRadiusPx = cornerRadiusPx,
                                strokeWidthPx = borderWidthPx
                            )
                            drawGlowRoundRect(
                                color = PopupColors.CyanAccent.copy(alpha = 0.07f),
                                blurRadiusPx = scale.px(28f),
                                cornerRadiusPx = cornerRadiusPx,
                                strokeWidthPx = borderWidthPx
                            )
                            drawGlowRoundRect(
                                color = PopupColors.CyanAccent.copy(alpha = 0.3f),
                                blurRadiusPx = scale.px(3f),
                                cornerRadiusPx = cornerRadiusPx,
                                strokeWidthPx = borderWidthPx
                            )
                        }
                    } else {
                        Modifier
                    }
                )
        ) {
            Box(
                modifier = Modifier
                    .matchParentSize()
                    .clip(RoundedCornerShape(cornerRadius))
                    .background(Color(0xFF060C14))
                    .border(
                        borderWidth,
                        if (item.enhanced) PopupColors.OnCardBorder else PopupColors.OffCardBorder,
                        RoundedCornerShape(cornerRadius)
                    )
            ) {
                if (resId != 0) {
                    Image(
                        painter = painterResource(id = resId),
                        contentDescription = item.label,
                        contentScale = ContentScale.Crop,
                        colorFilter = ColorFilter.colorMatrix(
                            if (item.enhanced) OnColorMatrix else OffColorMatrix
                        ),
                        modifier = Modifier.fillMaxSize()
                    )
                }
            }
        }
    }
}

@Composable
private fun ButtonRow(
    buttons: List<PopupButtonItem>,
    scale: UiScale,
    buttonFocusRequesters: List<FocusRequester>,
    upTarget: FocusRequester?,
    onButtonClick: (action: String) -> Unit
) {
    var focusedIndex by remember { mutableIntStateOf(0) }

    Row(
        horizontalArrangement = Arrangement.spacedBy(
            scale.dp(16f),
            Alignment.CenterHorizontally
        ),
        modifier = Modifier
            .fillMaxWidth()
            .wrapContentHeight()
            .padding(
                top = scale.dp(32f),
                bottom = scale.dp(40f),
                start = scale.dp(48f),
                end = scale.dp(48f)
            )
    ) {
        buttons.forEachIndexed { index, button ->
            PopupPillButton(
                text = button.text,
                scale = scale,
                isFocused = focusedIndex == index,
                focusRequester = buttonFocusRequesters[index],
                leftTarget = buttonFocusRequesters.getOrNull(index - 1),
                rightTarget = buttonFocusRequesters.getOrNull(index + 1),
                upTarget = upTarget,
                onFocused = { focusedIndex = index },
                onClick = { onButtonClick(button.action) }
            )
        }
    }

    LaunchedEffect(buttonFocusRequesters.size) {
        buttonFocusRequesters.firstOrNull()?.requestFocus()
    }
}

@Composable
private fun PopupPillButton(
    text: String,
    scale: UiScale,
    isFocused: Boolean,
    focusRequester: FocusRequester,
    leftTarget: FocusRequester?,
    rightTarget: FocusRequester?,
    upTarget: FocusRequester?,
    onFocused: () -> Unit,
    onClick: () -> Unit
) {
    val backgroundColor by animateColorAsState(
        targetValue = if (isFocused) PopupColors.ButtonFocusedBg else PopupColors.ButtonUnfocusedBg,
        label = "btnBg"
    )
    val textColor by animateColorAsState(
        targetValue = if (isFocused) PopupColors.ButtonFocusedText else PopupColors.ButtonUnfocusedText,
        label = "btnText"
    )
    val scaleFactor by animateFloatAsState(
        targetValue = if (isFocused) 1.03f else 1f,
        label = "btnScale"
    )

    val buttonShape = RoundedCornerShape(scale.dp(50f))

    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .defaultMinSize(minWidth = scale.dp(220f))
            .wrapContentHeight()
            .focusRequester(focusRequester)
            .onFocusChanged { state ->
                if (state.isFocused) onFocused()
            }
            .focusable()
            .focusProperties {
                if (leftTarget != null) left = leftTarget
                if (rightTarget != null) right = rightTarget
                if (upTarget != null) up = upTarget
            }
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyDown &&
                    (event.key == Key.Enter || event.key == Key.DirectionCenter)
                ) {
                    onClick()
                    true
                } else {
                    false
                }
            }
            .graphicsLayer {
                scaleX = scaleFactor
                scaleY = scaleFactor
            }
            .then(
                if (isFocused) {
                    Modifier.shadow(
                        elevation = scale.dp(8f),
                        shape = buttonShape,
                        clip = false,
                        ambientColor = Color.White.copy(alpha = 0.12f),
                        spotColor = Color.White.copy(alpha = 0.12f)
                    )
                } else {
                    Modifier
                }
            )
            .clip(buttonShape)
            .background(backgroundColor)
            .then(
                if (!isFocused) {
                    Modifier.border(scale.dp(1f), PopupColors.ModalBorder, buttonShape)
                } else {
                    Modifier
                }
            )
            .padding(
                vertical = scale.dp(16f),
                horizontal = scale.dp(52f)
            )
    ) {
        Text(
            text = text,
            color = textColor,
            fontSize = scale.sp(24f),
            fontWeight = FontWeight.SemiBold,
            letterSpacing = scale.sp(0.48f),
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun BlurredBackground(
    bitmap: Bitmap,
    blurRadiusPx: Float,
    modifier: Modifier = Modifier
) {
    val colorFilterMatrix = remember {
        ColorMatrix().apply {
            setToSaturation(1.5f)
            timesAssign(
                ColorMatrix(
                    floatArrayOf(
                        0.65f, 0f, 0f, 0f, 0f,
                        0f, 0.65f, 0f, 0f, 0f,
                        0f, 0f, 0.65f, 0f, 0f,
                        0f, 0f, 0f, 1f, 0f
                    )
                )
            )
        }
    }
    val safeRadius = blurRadiusPx.coerceAtLeast(1f)

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        Image(
            bitmap = bitmap.asImageBitmap(),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            colorFilter = ColorFilter.colorMatrix(colorFilterMatrix),
            modifier = modifier.graphicsLayer {
                renderEffect = RenderEffect.createBlurEffect(
                    safeRadius,
                    safeRadius,
                    Shader.TileMode.CLAMP
                ).asComposeRenderEffect()
            }
        )
    } else {
        val blurredBitmap = remember(bitmap, safeRadius) {
            stackBlur(bitmap, safeRadius.roundToInt())
        }
        Image(
            bitmap = blurredBitmap.asImageBitmap(),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            colorFilter = ColorFilter.colorMatrix(colorFilterMatrix),
            modifier = modifier
        )
    }
}

private fun DrawScope.drawGlowRoundRect(
    color: Color,
    blurRadiusPx: Float,
    cornerRadiusPx: Float,
    strokeWidthPx: Float
) {
    if (blurRadiusPx <= 0f || strokeWidthPx <= 0f) return
    drawIntoCanvas { canvas ->
        val paint = Paint().apply {
            isAntiAlias = true
            style = Paint.Style.STROKE
            strokeWidth = strokeWidthPx
            this.color = color.toArgb()
            maskFilter = BlurMaskFilter(blurRadiusPx, BlurMaskFilter.Blur.NORMAL)
        }
        val inset = strokeWidthPx / 2f
        val rect = RectF(
            inset,
            inset,
            size.width - inset,
            size.height - inset
        )
        canvas.nativeCanvas.drawRoundRect(rect, cornerRadiusPx, cornerRadiusPx, paint)
    }
}

private fun stackBlur(source: Bitmap, radius: Int): Bitmap {
    val safeRadius = radius.coerceAtLeast(1)
    val bitmap = source.copy(Bitmap.Config.ARGB_8888, true)
    val w = bitmap.width
    val h = bitmap.height
    val pixels = IntArray(w * h)
    bitmap.getPixels(pixels, 0, w, 0, 0, w, h)

    val div = 2 * safeRadius + 1
    val temp = IntArray(w * h)

    for (y in 0 until h) {
        var rAcc = 0
        var gAcc = 0
        var bAcc = 0
        for (x in -safeRadius..safeRadius) {
            val px = pixels[y * w + x.coerceIn(0, w - 1)]
            rAcc += (px shr 16) and 0xFF
            gAcc += (px shr 8) and 0xFF
            bAcc += px and 0xFF
        }
        for (x in 0 until w) {
            temp[y * w + x] = (0xFF shl 24) or
                ((rAcc / div) shl 16) or
                ((gAcc / div) shl 8) or
                (bAcc / div)
            val addX = (x + safeRadius + 1).coerceAtMost(w - 1)
            val subX = (x - safeRadius).coerceAtLeast(0)
            val addPx = pixels[y * w + addX]
            val subPx = pixels[y * w + subX]
            rAcc += ((addPx shr 16) and 0xFF) - ((subPx shr 16) and 0xFF)
            gAcc += ((addPx shr 8) and 0xFF) - ((subPx shr 8) and 0xFF)
            bAcc += (addPx and 0xFF) - (subPx and 0xFF)
        }
    }

    for (x in 0 until w) {
        var rAcc = 0
        var gAcc = 0
        var bAcc = 0
        for (y in -safeRadius..safeRadius) {
            val px = temp[y.coerceIn(0, h - 1) * w + x]
            rAcc += (px shr 16) and 0xFF
            gAcc += (px shr 8) and 0xFF
            bAcc += px and 0xFF
        }
        for (y in 0 until h) {
            pixels[y * w + x] = (0xFF shl 24) or
                ((rAcc / div) shl 16) or
                ((gAcc / div) shl 8) or
                (bAcc / div)
            val addY = (y + safeRadius + 1).coerceAtMost(h - 1)
            val subY = (y - safeRadius).coerceAtLeast(0)
            val addPx = temp[addY * w + x]
            val subPx = temp[subY * w + x]
            rAcc += ((addPx shr 16) and 0xFF) - ((subPx shr 16) and 0xFF)
            gAcc += ((addPx shr 8) and 0xFF) - ((subPx shr 8) and 0xFF)
            bAcc += (addPx and 0xFF) - (subPx and 0xFF)
        }
    }

    bitmap.setPixels(pixels, 0, w, 0, 0, w, h)
    return bitmap
}