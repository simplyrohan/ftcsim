import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

/** Tone mapping and display-space color grading for every viewport. */
export class ViewerColorGrade {
  private target:THREE.WebGLRenderTarget;
  private size=new THREE.Vector2();
  private pass=new ShaderPass({
    name:'ViewerColorGrade',
    uniforms:{tDiffuse:{value:null},vibrance:{value:.75},shadows:{value:.5},highlights:{value:.12},midtoneLift:{value:.03}},
    vertexShader:`
      varying vec2 vUv;
      void main() {
        vUv=uv;
        gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);
      }
    `,
    fragmentShader:`
      uniform sampler2D tDiffuse;
      uniform float vibrance;
      uniform float shadows;
      uniform float highlights;
      uniform float midtoneLift;
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
        float peak=max(color.r,max(color.g,color.b));
        float range=peak-min(color.r,min(color.g,color.b));
        float saturation=range/max(peak,0.00001);
        // Keep strong shadow contrast from muddying colored surfaces.
        float colorfulness=smoothstep(0.04,0.2,range);
        float shadowWeight=1.0-0.45*colorfulness;
        float graded=luminance-shadows*shadowWeight*luminance*(1.0-smoothstep(0.08,0.5,luminance));
        graded+=midtoneLift*4.0*luminance*(1.0-luminance)*(1.0+colorfulness);
        graded-=highlights*smoothstep(0.65,1.0,luminance);
        color*=graded/max(luminance,0.00001);
        vec3 chroma=color-vec3(graded);
        float boost=1.0+vibrance*(1.0-saturation);
        // Limit chroma uniformly to preserve hue instead of clipping individual channels.
        float lower=graded/max(-min(chroma.r,min(chroma.g,chroma.b)),0.00001);
        float upper=(1.0-graded)/max(max(chroma.r,max(chroma.g,chroma.b)),0.00001);
        color=vec3(graded)+chroma*min(boost,min(lower,upper));
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
