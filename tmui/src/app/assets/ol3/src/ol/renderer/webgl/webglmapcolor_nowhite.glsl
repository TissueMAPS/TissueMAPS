//! NAMESPACE=ol.renderer.webgl.map.shader.ColorNoWhite
//! CLASS=ol.renderer.webgl.map.shader.ColorNoWhite


//! COMMON
varying vec2 v_texCoord;


//! VERTEX
attribute vec2 a_position;
attribute vec2 a_texCoord;

uniform mat4 u_texCoordMatrix;
uniform mat4 u_projectionMatrix;

void main(void) {
  gl_Position = u_projectionMatrix * vec4(a_position, 0., 1.);
  v_texCoord = (u_texCoordMatrix * vec4(a_texCoord, 0., 1.)).st;
}


//! FRAGMENT
// @see https://svn.webkit.org/repository/webkit/trunk/Source/WebCore/platform/graphics/filters/skia/SkiaImageFilterBuilder.cpp
uniform mat4 u_colorMatrix;
uniform float u_opacity;
uniform sampler2D u_texture;

uniform float u_min;
uniform float u_max;
uniform vec3 u_color;


void main(void) {
  vec4 texColor = texture2D(u_texture, v_texCoord);

  // If the tile is white at this position dont render it
  if (texColor.r > 0.20 && texColor.g > 0.20 && texColor.b > 0.20) {
    discard;
  }

  vec3 newColRGB = (u_colorMatrix * vec4(texColor.rgb, 1.)).rgb;

  newColRGB = (newColRGB - u_min) / (u_max - u_min);
  gl_FragColor.rgb =  newColRGB * u_color;
  gl_FragColor.a = texColor.a * u_opacity;
}
