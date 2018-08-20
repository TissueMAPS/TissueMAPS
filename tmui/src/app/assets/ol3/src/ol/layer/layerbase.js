goog.provide('ol.layer.Base');
goog.provide('ol.layer.LayerProperty');
goog.provide('ol.layer.LayerState');

goog.require('goog.math');
goog.require('goog.object');
goog.require('ol.Object');
goog.require('ol.source.State');

goog.require('goog.color.Rgb');

/**
 * @enum {string}
 */
ol.layer.LayerProperty = {
  BRIGHTNESS: 'brightness',
  CONTRAST: 'contrast',
  HUE: 'hue',
  OPACITY: 'opacity',
  SATURATION: 'saturation',
  VISIBLE: 'visible',
  EXTENT: 'extent',
  MAX_RESOLUTION: 'maxResolution',
  MIN_RESOLUTION: 'minResolution',
  ADDITIVE_BLEND: 'additiveBlend',
  DRAW_BLACK_PIXELS: 'drawBlackPixels',
  DRAW_WHITE_PIXELS: 'drawWhitePixels',
  SOURCE: 'source',
  COLOR: 'color',
  MAX: 'max',
  MIN: 'min'
};


/**
 * @typedef {{layer: ol.layer.Layer,
 *            brightness: number,
 *            contrast: number,
 *            hue: number,
 *            opacity: number,
 *            saturation: number,
 *            sourceState: ol.source.State,
 *            visible: boolean,
 *            managed: boolean,
 *            extent: (ol.Extent|undefined),
 *            color: goog.color.Rgb,
 *            min: number,
 *            max: number,
 *            additiveBlend: boolean,
 *            drawBlackPixels: boolean,
 *            drawWhitePixels: boolean,
 *            maxResolution: number,
 *            minResolution: number}}
 */
ol.layer.LayerState;


/**
 * @classdesc
 * Abstract base class; normally only used for creating subclasses and not
 * instantiated in apps.
 * Note that with `ol.layer.Base` and all its subclasses, any property set in
 * the options is set as a {@link ol.Object} property on the layer object, so
 * is observable, and has get/set accessors.
 *
 * @constructor
 * @extends {ol.Object}
 * @param {olx.layer.BaseOptions} options Layer options.
 * @api stable
 */
ol.layer.Base = function(options) {

  goog.base(this);

  /**
   * @type {Object.<string, *>}
   */
  var properties = goog.object.clone(options);
  properties[ol.layer.LayerProperty.BRIGHTNESS] =
      goog.isDef(options.brightness) ? options.brightness : 0;
  properties[ol.layer.LayerProperty.CONTRAST] =
      goog.isDef(options.contrast) ? options.contrast : 1;
  properties[ol.layer.LayerProperty.HUE] =
      goog.isDef(options.hue) ? options.hue : 0;
  properties[ol.layer.LayerProperty.OPACITY] =
      goog.isDef(options.opacity) ? options.opacity : 1;
  properties[ol.layer.LayerProperty.SATURATION] =
      goog.isDef(options.saturation) ? options.saturation : 1;
  properties[ol.layer.LayerProperty.VISIBLE] =
      goog.isDef(options.visible) ? options.visible : true;
  properties[ol.layer.LayerProperty.MAX_RESOLUTION] =
      goog.isDef(options.maxResolution) ? options.maxResolution : Infinity;
  properties[ol.layer.LayerProperty.MIN_RESOLUTION] =
      goog.isDef(options.minResolution) ? options.minResolution : 0;

  properties[ol.layer.LayerProperty.COLOR] =
      goog.isDef(options.color) ? options.color : [1, 1, 1];
  properties[ol.layer.LayerProperty.MAX] =
      goog.isDef(options.max) ? options.max : 1;
  properties[ol.layer.LayerProperty.MIN] =
      goog.isDef(options.min) ? options.min : 0;
  properties[ol.layer.LayerProperty.ADDITIVE_BLEND] =
      goog.isDef(options.additiveBlend) ? options.additiveBlend : false;
  properties[ol.layer.LayerProperty.DRAW_BLACK_PIXELS] =
      goog.isDef(options.drawBlackPixels) ? options.drawBlackPixels : true;
  properties[ol.layer.LayerProperty.DRAW_WHITE_PIXELS] =
      goog.isDef(options.drawWhitePixels) ? options.drawWhitePixels : true;

  this.setProperties(properties);
};
goog.inherits(ol.layer.Base, ol.Object);


/**
 * Return the brightness of the layer.
 * @return {number} The brightness of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getBrightness = function() {
  return /** @type {number} */ (this.get(ol.layer.LayerProperty.BRIGHTNESS));
};


/**
 * Return the contrast of the layer.
 * @return {number} The contrast of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getContrast = function() {
  return /** @type {number} */ (this.get(ol.layer.LayerProperty.CONTRAST));
};


/**
 * Return the hue of the layer.
 * @return {number} The hue of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getHue = function() {
  return /** @type {number} */ (this.get(ol.layer.LayerProperty.HUE));
};


/**
 * @return {ol.layer.LayerState} Layer state.
 */
ol.layer.Base.prototype.getLayerState = function() {
  var brightness = this.getBrightness();
  var contrast = this.getContrast();
  var hue = this.getHue();
  var opacity = this.getOpacity();
  var saturation = this.getSaturation();
  var sourceState = this.getSourceState();
  var visible = this.getVisible();
  var extent = this.getExtent();
  var maxResolution = this.getMaxResolution();
  var minResolution = this.getMinResolution();

  // ADDED
  var min = this.getMin();
  var max = this.getMax();
  var color = this.getColor();
  var additiveBlend = this.getAdditiveBlend();
  var drawBlackPixels = this.getDrawBlackPixels();
  var drawWhitePixels = this.getDrawWhitePixels();

  return {
    layer: /** @type {ol.layer.Layer} */ (this),
    brightness: goog.math.clamp(brightness, -1, 1),
    contrast: Math.max(contrast, 0),
    hue: hue,
    opacity: goog.math.clamp(opacity, 0, 1),
    saturation: Math.max(saturation, 0),
    sourceState: sourceState,
    visible: visible,
    managed: true,
    extent: extent,
    maxResolution: goog.isDef(maxResolution) ? maxResolution : Infinity,
    minResolution: goog.isDef(minResolution) ? Math.max(minResolution, 0) : 0,

    color: goog.isDef(color) ? color : [1, 1, 1],
    min: goog.isDef(min) ? min : 0,
    max: goog.isDef(max) ? max : 1,
    additiveBlend: goog.isDef(additiveBlend) ? additiveBlend : false,
    drawBlackPixels: goog.isDef(drawBlackPixels) ? drawBlackPixels : true,
    drawWhitePixels: goog.isDef(drawWhitePixels) ? drawWhitePixels : true
  };
};


/**
 * @param {Array.<ol.layer.Layer>=} opt_array Array of layers (to be
 *     modified in place).
 * @return {Array.<ol.layer.Layer>} Array of layers.
 */
ol.layer.Base.prototype.getLayersArray = goog.abstractMethod;


/**
 * @param {Array.<ol.layer.LayerState>=} opt_states Optional list of layer
 *     states (to be modified in place).
 * @return {Array.<ol.layer.LayerState>} List of layer states.
 */
ol.layer.Base.prototype.getLayerStatesArray = goog.abstractMethod;


/**
 * Return the {@link ol.Extent extent} of the layer or `undefined` if it
 * will be visible regardless of extent.
 * @return {ol.Extent|undefined} The layer extent.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.getExtent = function() {
  return /** @type {ol.Extent|undefined} */ (
      this.get(ol.layer.LayerProperty.EXTENT));
};


/**
 * Return the maximum resolution of the layer.
 * @return {number} The maximum resolution of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.getMaxResolution = function() {
  return /** @type {number} */ (
      this.get(ol.layer.LayerProperty.MAX_RESOLUTION));
};


/**
 * Return the minimum resolution of the layer.
 * @return {number} The minimum resolution of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.getMinResolution = function() {
  return /** @type {number} */ (
      this.get(ol.layer.LayerProperty.MIN_RESOLUTION));
};


/**
 * Return the opacity of the layer (between 0 and 1).
 * @return {number} The opacity of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.getOpacity = function() {
  return /** @type {number} */ (this.get(ol.layer.LayerProperty.OPACITY));
};


/**
 * Return the saturation of the layer.
 * @return {number} The saturation of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getSaturation = function() {
  return /** @type {number} */ (this.get(ol.layer.LayerProperty.SATURATION));
};


/**
 * @return {ol.source.State} Source state.
 */
ol.layer.Base.prototype.getSourceState = goog.abstractMethod;


/**
 * Return the visibility of the layer (`true` or `false`).
 * @return {boolean} The visibility of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.getVisible = function() {
  return /** @type {boolean} */ (this.get(ol.layer.LayerProperty.VISIBLE));
};


/**
 * Adjust the layer brightness.  A value of -1 will render the layer completely
 * black.  A value of 0 will leave the brightness unchanged.  A value of 1 will
 * render the layer completely white.  Other values are linear multipliers on
 * the effect (values are clamped between -1 and 1).
 *
 * The filter effects draft [1] says the brightness function is supposed to
 * render 0 black, 1 unchanged, and all other values as a linear multiplier.
 *
 * The current WebKit implementation clamps values between -1 (black) and 1
 * (white) [2].  There is a bug open to change the filter effect spec [3].
 *
 * TODO: revisit this if the spec is still unmodified before we release
 *
 * [1] https://dvcs.w3.org/hg/FXTF/raw-file/tip/filters/index.html
 * [2] https://github.com/WebKit/webkit/commit/8f4765e569
 * [3] https://www.w3.org/Bugs/Public/show_bug.cgi?id=15647
 *
 * @param {number} brightness The brightness of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setBrightness = function(brightness) {
  this.set(ol.layer.LayerProperty.BRIGHTNESS, brightness);
};


/**
 * Adjust the layer contrast.  A value of 0 will render the layer completely
 * grey.  A value of 1 will leave the contrast unchanged.  Other values are
 * linear multipliers on the effect (and values over 1 are permitted).
 *
 * @param {number} contrast The contrast of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setContrast = function(contrast) {
  this.set(ol.layer.LayerProperty.CONTRAST, contrast);
};


/**
 * Apply a hue-rotation to the layer.  A value of 0 will leave the hue
 * unchanged.  Other values are radians around the color circle.
 * @param {number} hue The hue of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setHue = function(hue) {
  this.set(ol.layer.LayerProperty.HUE, hue);
};


/**
 * Set the extent at which the layer is visible.  If `undefined`, the layer
 * will be visible at all extents.
 * @param {ol.Extent|undefined} extent The extent of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.setExtent = function(extent) {
  this.set(ol.layer.LayerProperty.EXTENT, extent);
};


/**
 * Set the maximum resolution at which the layer is visible.
 * @param {number} maxResolution The maximum resolution of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.setMaxResolution = function(maxResolution) {
  this.set(ol.layer.LayerProperty.MAX_RESOLUTION, maxResolution);
};


/**
 * Set the minimum resolution at which the layer is visible.
 * @param {number} minResolution The minimum resolution of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.setMinResolution = function(minResolution) {
  this.set(ol.layer.LayerProperty.MIN_RESOLUTION, minResolution);
};


/**
 * Set the opacity of the layer, allowed values range from 0 to 1.
 * @param {number} opacity The opacity of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.setOpacity = function(opacity) {
  this.set(ol.layer.LayerProperty.OPACITY, opacity);
};


/**
 * Adjust layer saturation.  A value of 0 will render the layer completely
 * unsaturated.  A value of 1 will leave the saturation unchanged.  Other
 * values are linear multipliers of the effect (and values over 1 are
 * permitted).
 *
 * @param {number} saturation The saturation of the layer.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setSaturation = function(saturation) {
  this.set(ol.layer.LayerProperty.SATURATION, saturation);
};

/**
 * Set the visibility of the layer (`true` or `false`).
 * @param {boolean} visible The visibility of the layer.
 * @observable
 * @api stable
 */
ol.layer.Base.prototype.setVisible = function(visible) {
  this.set(ol.layer.LayerProperty.VISIBLE, visible);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setVisible',
    ol.layer.Base.prototype.setVisible);



/**
 * @return {goog.color.Rgb|undefined} The color with which this layer should be dyed.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getColor = function() {
  return /** @type {goog.color.Rgb|undefined} */ (this.get(
    ol.layer.LayerProperty.COLOR));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getColor',
    ol.layer.Base.prototype.getColor);

/**
 * @param {goog.color.Rgb|null} color The color with which to dye the layer.
 *  If the argument is null, the image won't be colored.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setColor = function(color) {
  if (!goog.isNull(color)) {
    this.set(ol.layer.LayerProperty.COLOR, color);
  } else {
    // Setting [1.0, 1.0, 1.0] will result in the grayscale image
    // being rendered as an RGB image with equal amounts of equal color
    // (thus just creating a gray RGB image).
    this.set(ol.layer.LayerProperty.COLOR, [1.0, 1.0, 1.0]);
  }
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setColor',
    ol.layer.Base.prototype.setColor);



/**
 * @return {number|undefined} Min.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getMin = function() {
  return /** @type {number|undefined} */ (this.get(
    ol.layer.LayerProperty.MIN));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getMin',
    ol.layer.Base.prototype.getMin);

/**
 * @param {number} min Min.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setMin = function(min) {
  if (min > this.getMax()) {
      this.setMax(min);
  }
  this.set(ol.layer.LayerProperty.MIN, min);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setMin',
    ol.layer.Base.prototype.setMin);



/**
 * @return {number|undefined} Max.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getMax = function() {
  return /** @type {number|undefined} */ (this.get(
    ol.layer.LayerProperty.MAX));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getMax',
    ol.layer.Base.prototype.getMax);

/**
 * @param {number} max Max.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setMax = function(max) {
  if (max < this.getMin()) {
      this.setMin(max);
  }
  this.set(ol.layer.LayerProperty.MAX, max);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setMax',
    ol.layer.Base.prototype.setMax);

/**
 * @return {boolean|undefined} If the layer should be blended additively.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getAdditiveBlend = function() {
  return /** @type {boolean|undefined} */ (this.get(
    ol.layer.LayerProperty.ADDITIVE_BLEND));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getAdditiveBlend',
    ol.layer.Base.prototype.getAdditiveBlend);

/**
 * @param {boolean} doBlend If the layer should be blended additively.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setAdditiveBlend = function(doBlend) {
  this.set(ol.layer.LayerProperty.ADDITIVE_BLEND, doBlend);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setAdditiveBlend',
    ol.layer.Base.prototype.setAdditiveBlend);


/**
 * @return {boolean|undefined} If black pixels should be drawn.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getDrawBlackPixels = function() {
  return /** @type {boolean|undefined} */ (this.get(
    ol.layer.LayerProperty.DRAW_BLACK_PIXELS));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getDrawBlackPixels',
    ol.layer.Base.prototype.getDrawBlackPixels);

/**
 * @param {boolean} doDraw If black pxiels should be drawn.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setDrawBlackPixels = function(doDraw) {
  this.set(ol.layer.LayerProperty.DRAW_BLACK_PIXELS, doDraw);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setDrawBlackPixels',
    ol.layer.Base.prototype.setDrawBlackPixels);


/**
 * @return {boolean|undefined} If white pixels should be drawn.
 * @observable
 * @api
 */
ol.layer.Base.prototype.getDrawWhitePixels = function() {
  return /** @type {boolean|undefined} */ (this.get(
    ol.layer.LayerProperty.DRAW_WHITE_PIXELS));
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'getDrawWhitePixels',
    ol.layer.Base.prototype.getDrawWhitePixels);

/**
 * @param {boolean} doDraw If white pixels should be drawn.
 * @observable
 * @api
 */
ol.layer.Base.prototype.setDrawWhitePixels = function(doDraw) {
  this.set(ol.layer.LayerProperty.DRAW_WHITE_PIXELS, doDraw);
};
goog.exportProperty(
    ol.layer.Base.prototype,
    'setDrawWhitePixels',
    ol.layer.Base.prototype.setDrawWhitePixels);
