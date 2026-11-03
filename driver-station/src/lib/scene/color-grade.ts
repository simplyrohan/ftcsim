import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

/** One output pass for tone mapping and subtle display-space color grading. */
export class ViewerColorGrade {
  private target:THREE.WebGLRenderTarget;
  private size=new THREE.Vector2();
  private pass=new ShaderPass({
    name:'ViewerColorGrade',
    uniforms:{tDiffuse:{value:null},saturation:{value:1.22},contrast:{value:.4}},
    vertexShader:`
      varying vec2 vUv;
      void main() {
        vUv=uv;
        gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);
      }
    `,
    fragmentShader:`
      uniform sampler2D tDiffuse;
      uniform float saturation;
      uniform float contrast;
      varying vec2 vUv;
      void main() {
        vec4 source=texture2D(tDiffuse,vUv);
        if(source.a<0.00001) { gl_FragColor=vec4(0.0); return; }
        // Grade straight color, then restore premultiplication for the transparent canvas.
        gl_FragColor=vec4(source.rgb/source.a,source.a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        vec3 color=gl_FragColor.rgb;
        float luminance=dot(color,vec3(0.2126,0.7152,0.0722));
        color=clamp(mix(vec3(luminance),color,saturation),0.0,1.0);
        color+=(color-0.5)*color*(1.0-color)*contrast;
        gl_FragColor.rgb=color*source.a;
      }
    `,
  });

  constructor(private renderer:THREE.WebGLRenderer) {
    this.target=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,samples:Math.min(4,renderer.capabilities.maxSamples)});
    this.pass.renderToScreen=true;
  }
  resize() { this.renderer.getDrawingBufferSize(this.size);this.target.setSize(this.size.x,this.size.y); }
  render(scene:THREE.Scene,camera:THREE.Camera) {
    this.renderer.setRenderTarget(this.target);
    this.renderer.render(scene,camera);
    this.pass.render(this.renderer,this.target,this.target,0,false);
  }
  dispose() { this.pass.dispose();this.target.dispose(); }
}
