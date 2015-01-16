goog.provide('ol.layer.GrayscaleTile');

goog.require('ol.layer.Tile');
goog.require('goog.color.Rgb');


/**
 * @enum {string}
 */
ol.layer.GrayscaleTileProperty = {
  COLOR: 'color'
};


/**
 * @classdesc
 * Modified version of a tile layer for TissueMAPS that provides a setable color attribute
 *  and should be used with 8 bit grayscale images (16 bit depth not supported by WebGL).
 *  This layer can only be used when the renderer is set to WebGL!
 * @constructor
 * @extends {ol.layer.Tile}
 * @fires ol.render.Event
 * @param {olx.layer.TileOptions=} opt_options Tile layer options.
 * @api stable
 */
ol.layer.GrayscaleTile = function(opt_options) {
  var options = goog.isDef(opt_options) ? opt_options : {};
  goog.base(this, /** @type {olx.layer.TileOptions} */ (opt_options));

  this.setColor(goog.isDef(options.color) ? options.color : [1, 1, 1]);

};
goog.inherits(ol.layer.GrayscaleTile, ol.layer.Tile);


/**
 * @return {goog.color.Rgb} The color with which this layer should be dyed.
 * @observable
 * @api
 */
ol.layer.GrayscaleTile.prototype.getColor = function() {
  return /** @type {goog.color.Rgb} */ (this.get(
    ol.layer.GrayscaleTileProperty.COLOR));
};
goog.exportProperty(
    ol.layer.GrayscaleTile.prototype,
    'getcolor',
    ol.layer.GrayscaleTile.prototype.getColor);


/**
 * @param {goog.color.Rgb|null} color The color with which to dye the layer.
 *  If the argument is null, the image won't be colored.
 * @observable
 * @api
 */
ol.layer.GrayscaleTile.prototype.setColor = function(color) {
  if (!goog.isNull(color)) {
    this.set(ol.layer.GrayscaleTileProperty.COLOR, color);
  } else {
    // Setting [1.0, 1.0, 1.0] will result in the grayscale image
    // being rendered as an RGB image with equal amounts of equal color
    // (thus just creating a gray RGB image).
    this.set(ol.layer.GrayscaleTileProperty.COLOR, [1.0, 1.0, 1.0]);
  }
};
goog.exportProperty(
    ol.layer.GrayscaleTile.prototype,
    'setColor',
    ol.layer.GrayscaleTile.prototype.setColor);

